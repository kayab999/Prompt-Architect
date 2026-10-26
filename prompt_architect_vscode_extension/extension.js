const vscode = require('vscode');
const axios = require('axios');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  console.log('Congratulations, your extension "prompt-architect-vscode" is now active!');

  let disposable = vscode.commands.registerCommand('promptArchitect.refine', async () => {
    const editor = vscode.window.activeTextEditor;
    if (editor) {
      const selection = editor.selection;
      const text = editor.document.getText(selection);

      if (!text) {
        vscode.window.showWarningMessage('No text selected for refinement.');
        return;
      }

      vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "Refining prompt with Prompt Architect...",
        cancellable: false
      }, async (progress) => {
        try {
          // Assuming Prompt Architect backend is running on localhost:8000
          // You might want to make these configurable in extension settings
          const refinerModel = 'tinyllama:latest'; // Example refiner model
          const targetModel = 'General'; // Example target model

          const res = await axios.post('http://localhost:8000/optimize', {
            prompt: text,
            refiner_model: refinerModel,
            target_model: targetModel,
            intent: 'general'
          });

          editor.edit(editBuilder => {
            editBuilder.replace(selection, res.data.optimized_prompt);
          });
          vscode.window.showInformationMessage('Prompt refined successfully!');
        } catch (err) {
          vscode.window.showErrorMessage('Error refining prompt: ' + (err.response?.data?.detail || err.message));
        }
      });
    }
  });

  context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
}
