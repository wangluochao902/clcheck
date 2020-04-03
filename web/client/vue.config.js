const MonacoWebpackPlugin = require('monaco-editor-webpack-plugin')

module.exports = {
  chainWebpack: config => {
    config.plugin('monaco-editor').use(MonacoWebpackPlugin, [
      {
        // Languages are loaded on demand at runtime
        languages: ['shell', 'dockerfile'],
        features: [
            "accessibilityHelp",
            "autoClosingBrackets",
            "bracketMatching",
            "caretOperations",
            "clipboard",
            "codeAction",
            "codelens",
            "colorDetector",
            "comment",
            "contextmenu",
            "coreCommands",
            "cursorUndo",
            "dnd",
            "find",
            "folding",
            "fontZoom",
            "format",
            "gotoError",
            "gotoLine",
            "!gotoSymbol",
            "hover",
            "iPadShowKeyboard",
            "inPlaceReplace",
            "inspectTokens",
            "linesOperations",
            "links",
            "multicursor",
            "parameterHints",
            "quickCommand",
            "quickOutline",
            "referenceSearch",
            "rename",
            "smartSelect",
            "snippets",
            "suggest",
            "toggleHighContrast",
            "toggleTabFocusMode",
            "transpose",
            "wordHighlighter",
            "wordOperations",
            "wordPartOperations"
          ]
      }
    ])
  }
}