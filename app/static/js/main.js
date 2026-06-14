document.addEventListener("DOMContentLoaded", () => {
	// Bind submit behavior after the DOM is ready so progressive enhancement does not break server rendering.
	const form = document.getElementById("study-form");
	if (!form) {
		return;
	}

	// Read UI text from markup to keep loading-state wording configurable from templates.
	const button = form.querySelector(".submit-button");
	const buttonLabel = form.querySelector(".button-label");
	const loadingText = form.dataset.loadingText || "Generating study cards...";
	const defaultText = buttonLabel ? buttonLabel.textContent.trim() : "";

	// Form submission listener applies a one-way loading state to prevent duplicate requests.
	form.addEventListener("submit", () => {
		if (button) {
			// Button disabling prevents duplicate generation calls while backend providers are running.
			button.classList.add("is-loading");
			button.disabled = true;
		}

		if (buttonLabel) {
			// Label update communicates long-running generation progress to the user.
			buttonLabel.textContent = loadingText;
		}
	});

	console.log("AI Vocabulary Learning Tool loaded.");
	if (defaultText) {
		console.log("Submit button label:", defaultText);
	}
});
