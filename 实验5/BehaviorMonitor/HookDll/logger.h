#pragma once
#include <windows.h>

bool  LoggerInit(const char* logPath);
void  LoggerClose();
void  LogWrite(const char* apiFuncName,
    const wchar_t* filePath,
    DWORD desiredAccess,
    BOOL  retVal,
    HANDLE retHandle = INVALID_HANDLE_VALUE);