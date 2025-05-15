package com.x8bit.bitwarden.ui.auth.feature.enterprisesignon

import android.net.Uri
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.filterToOne
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.isDialog
import androidx.compose.ui.test.isPopup
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import com.x8bit.bitwarden.data.platform.repository.util.bufferedMutableSharedFlow
import com.x8bit.bitwarden.ui.platform.base.BaseComposeTest
import com.x8bit.bitwarden.ui.platform.base.util.asText
import com.x8bit.bitwarden.ui.platform.manager.intent.IntentManager
import com.x8bit.bitwarden.ui.util.assertNoPopupExists
import io.mockk.every
import io.mockk.just
import io.mockk.mockk
import io.mockk.runs
import io.mockk.verify
import junit.framework.TestCase.assertTrue
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import org.junit.Before
import org.junit.Test
import org.junit.jupiter.api.Assertions.assertEquals

class EnterpriseSignOnScreenTest : BaseComposeTest() {
    private var onNavigateBackCalled = false
    private var onNavigateToSetPasswordCalled = false
    private var onNavigateToTwoFactorLoginEmailAndOrgIdentifier: Pair<String, String>? = null
    private val mutableEventFlow = bufferedMutableSharedFlow<EnterpriseSignOnEvent>()
    private val mutableStateFlow = MutableStateFlow(DEFAULT_STATE)
    private val viewModel = mockk<EnterpriseSignOnViewModel>(relaxed = true) {
        every { eventFlow } returns mutableEventFlow
        every { stateFlow } returns mutableStateFlow
    }

    private val intentManager: IntentManager = mockk {
        every { startCustomTabsActivity(any()) } just runs
    }

    @Before
    fun setup() {
        composeTestRule.setContent {
            EnterpriseSignOnScreen(
                onNavigateBack = { onNavigateBackCalled = true },
                onNavigateToSetPassword = { onNavigateToSetPasswordCalled = true },
                onNavigateToTwoFactorLogin = { email, orgIdentifier ->
                    onNavigateToTwoFactorLoginEmailAndOrgIdentifier = email to orgIdentifier
                },
                viewModel = viewModel,
                intentManager = intentManager,
            )
        }
    }

    @Test
    fun `app bar log in click should send LogInClick action`() {
        composeTestRule.onNodeWithText("Log in").performClick()
        verify { viewModel.trySendAction(EnterpriseSignOnAction.LogInClick) }
    }

    @Test
    fun `close button click should send CloseButtonClick action`() {
        composeTestRule.onNodeWithContentDescription("Close").performClick()
        verify {
            viewModel.trySendAction(EnterpriseSignOnAction.CloseButtonClick)
        }
    }

    @Test
    fun `organization identifier input change should send OrgIdentifierInputChange action`() {
        val input = "input"
        composeTestRule.onNodeWithText("Organization identifier").performTextInput(input)
        verify {
            viewModel.trySendAction(EnterpriseSignOnAction.OrgIdentifierInputChange(input))
        }
    }

    @Test
    fun `organization identifier should change according to state`() {
        composeTestRule
            .onNodeWithText("Organization identifier")
            .assertTextEquals("Organization identifier", "")

        mutableStateFlow.update { it.copy(orgIdentifierInput = "test") }

        composeTestRule
            .onNodeWithText("Organization identifier")
            .assertTextEquals("Organization identifier", "test")
    }


    @Test
    fun `error dialog should be shown or hidden according to the state`() {
        composeTestRule.onNode(isDialog()).assertDoesNotExist()

        mutableStateFlow.update {
            it.copy(
                dialogState = EnterpriseSignOnState.DialogState.Error(
                    message = "Error dialog message".asText(),
                    title = "Error dialog title".asText(),
                ),
            )
        }

        composeTestRule.onNode(isDialog()).assertIsDisplayed()

        composeTestRule
            .onNodeWithText("An error has occurred.")
            .assert(hasAnyAncestor(isDialog()))
            .assertIsDisplayed()
        composeTestRule
            .onNodeWithText("Error dialog message")
            .assert(hasAnyAncestor(isDialog()))
            .assertIsDisplayed()
        composeTestRule
            .onNodeWithText("Ok")
            .assert(hasAnyAncestor(isDialog()))
            .assertIsDisplayed()
    }

    @Test
    fun `loading dialog should be displayed according to state`() {
        composeTestRule.assertNoPopupExists()
        composeTestRule.onNodeWithText("Loading").assertDoesNotExist()

        mutableStateFlow.update {
            it.copy(
                dialogState = EnterpriseSignOnState.DialogState.Loading(
                    message = "Loading".asText(),
                ),
            )
        }

        composeTestRule
            .onNodeWithText("Loading")
            .assertIsDisplayed()
            .assert(hasAnyAncestor(isPopup()))
    }


    @Test
    fun `error dialog OK click should send DialogDismiss action`() {
        mutableStateFlow.update {
            DEFAULT_STATE.copy(
                dialogState = EnterpriseSignOnState.DialogState.Error(
                    title = "Enterprise single sign-on".asText(),
                    message = "message".asText(),
                ),
            )
        }

        composeTestRule
            .onAllNodesWithText("Ok")
            .filterToOne(hasAnyAncestor(isDialog()))
            .performClick()
        verify { viewModel.trySendAction(EnterpriseSignOnAction.DialogDismiss) }
    }

    companion object {
        private val DEFAULT_STATE = EnterpriseSignOnState(
            dialogState = null,
            orgIdentifierInput = "",
            captchaToken = null,
        )
    }
}
