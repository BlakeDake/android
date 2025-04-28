import subprocess
import os
import platform

# Define the path to the text file relative to the script location or project root
test_file_path = 'ui_test_fqns.txt'
# Define the base Gradle command - run the task from the root project
# Use gradlew.bat on Windows, ./gradlew otherwise
gradle_executable = '.\\gradlew.bat' if platform.system() == "Windows" else './gradlew'
gradle_task = 'testStandardDebugUnitTest' # Task name common to modules
gradle_command_base = [gradle_executable, gradle_task, '--rerun-tasks']

# Check if the test file exists
if not os.path.exists(test_file_path):
    print(f"Error: Test file not found at '{test_file_path}'")
    exit(1)

# Read test class names from the file
try:
    with open(test_file_path, 'r') as f:
        # Filter out empty lines and potential comments (lines starting with #)
        test_classes = [
            line.strip() for line in f if line.strip() and not line.strip().startswith('#')
        ]
except Exception as e:
    print(f"Error reading file '{test_file_path}': {e}")
    exit(1)

if not test_classes:
    print(f"No valid test classes found in '{test_file_path}'.")
    exit(0)

# Build the full command list
gradle_command_full = gradle_command_base[:] # Start with a copy of the base command
for test_class in test_classes:
    # Gradle expects --tests followed by the pattern/class name as separate arguments
    gradle_command_full.append('--tests')
    gradle_command_full.append(test_class)

# Print the command being executed (optional, for verification)
print("Executing command:")
# Quote arguments containing spaces for better readability, though subprocess handles it
quoted_command = [f'"{arg}"' if ' ' in arg else arg for arg in gradle_command_full]
print(' '.join(quoted_command))
print("-" * 20)

# Execute the command
try:
    # On Windows, shell=True might still be needed if gradlew.bat relies on shell features
    # or if the path needs environment variable expansion, but it's generally safer
    # to avoid it if possible. Let's try without first. If gradlew.bat fails,
    # add shell=True back.
    # Ensure gradlew has execute permissions on non-Windows systems.
    result = subprocess.run(gradle_command_full, check=True, text=True)
    print("Gradle output:\n", result.stdout)
    if result.stderr:
        print("Gradle errors/warnings:\n", result.stderr)
    print("\nGradle task completed successfully.")

except subprocess.CalledProcessError as e:
    print(f"\nGradle task failed with exit code {e.returncode}")
    print("Gradle stdout:\n", e.stdout)
    print("Gradle stderr:\n", e.stderr)
    exit(e.returncode)
except FileNotFoundError:
    print(f"Error: '{gradle_executable}' command not found. Make sure you are in the project root directory and it exists.")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    exit(1)
