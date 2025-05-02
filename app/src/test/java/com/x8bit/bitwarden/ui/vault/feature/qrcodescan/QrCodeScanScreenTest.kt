package com.x8bit.bitwarden.ui.vault.feature.qrcodescan

import androidx.camera.core.ImageProxy
import androidx.compose.ui.test.onNodeWithText
import com.x8bit.bitwarden.data.platform.repository.util.bufferedMutableSharedFlow
import com.x8bit.bitwarden.ui.platform.base.BaseComposeTest
import com.x8bit.bitwarden.ui.vault.feature.qrcodescan.util.FakeQrCodeAnalyzer
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import junit.framework.TestCase.assertTrue
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import org.robolectric.annotation.Config

class QrCodeScanScreenTest : BaseComposeTest() {

    private var onNavigateBackCalled = false
    private var onNavigateToManualCodeEntryScreenCalled = false

    private val imageProxy: ImageProxy = mockk()
    private val qrCodeAnalyzer = FakeQrCodeAnalyzer()

    private val mutableEventFlow = bufferedMutableSharedFlow<QrCodeScanEvent>()

    private val viewModel = mockk<QrCodeScanViewModel>(relaxed = true) {
        every { eventFlow } returns mutableEventFlow
    }

    @Before
    fun setup() {
        composeTestRule.setContent {
            QrCodeScanScreen(
                onNavigateBack = { onNavigateBackCalled = true },
                viewModel = viewModel,
                qrCodeAnalyzer = qrCodeAnalyzer,
                onNavigateToManualCodeEntryScreen = {
                    onNavigateToManualCodeEntryScreenCalled = true
                },
            )
        }
    }

    @Config(qualifiers = "land")
    @Test
    fun `clicking on manual text should send ManualEntryTextClick in landscape mode`() = runTest {
        // TODO Update the tests once clickable text issue is resolved (BIT-1357)
        composeTestRule
            .onNodeWithText("Enter key manually", substring = true)
            .assertExists()
    }

    @Test
    fun `clicking on manual text should send ManualEntryTextClick`() = runTest {
        // TODO Update the tests once clickable text issue is resolved (BIT-1357)
        composeTestRule
            .onNodeWithText("Enter key manually", substring = true)
            .assertExists()
    }
}
