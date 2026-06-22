; NSIS custom script — runs after main app install
; Auto-downloads and silently installs Ollama on Windows

!macro customInstall
  DetailPrint "Checking for Ollama..."
  nsExec::ExecToStack 'cmd /c where ollama'
  Pop $0
  ${If} $0 != 0
    DetailPrint "Downloading Ollama AI engine..."
    inetc::get "https://ollama.com/download/OllamaSetup.exe" "$TEMP\OllamaSetup.exe" /END
    Pop $0
    ${If} $0 == "OK"
      DetailPrint "Installing Ollama silently..."
      ExecWait '"$TEMP\OllamaSetup.exe" /S'
      DetailPrint "Ollama installed successfully."
    ${Else}
      MessageBox MB_OK|MB_ICONINFORMATION "Could not download Ollama automatically.$\n$\nPlease visit https://ollama.com/download to install it manually after setup."
    ${EndIf}
  ${Else}
    DetailPrint "Ollama already installed. Skipping."
  ${EndIf}
!macroend

!macro customUnInstall
  ; Nothing extra on uninstall
!macroend
