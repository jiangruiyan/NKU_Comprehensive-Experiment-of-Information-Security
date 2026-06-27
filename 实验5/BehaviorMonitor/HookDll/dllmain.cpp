#include <windows.h>
#include <detours.h>
#include <stdio.h>
#include <wchar.h>
#include "logger.h"

#pragma comment(lib, "detours.lib")

// ================================================================
// 原始函数指针
// ================================================================
static HANDLE(WINAPI* Real_CreateFileW)(
    LPCWSTR, DWORD, DWORD,
    LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE) = CreateFileW;

static BOOL(WINAPI* Real_ReadFile)(
    HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED) = ReadFile;

static BOOL(WINAPI* Real_WriteFile)(
    HANDLE, LPCVOID, DWORD, LPDWORD, LPOVERLAPPED) = WriteFile;

static BOOL(WINAPI* Real_DeleteFileW)(
    LPCWSTR) = DeleteFileW;

static BOOL(WINAPI* Real_MoveFileW)(
    LPCWSTR, LPCWSTR) = MoveFileW;

static BOOL(WINAPI* Real_CopyFileW)(
    LPCWSTR, LPCWSTR, BOOL) = CopyFileW;

// ================================================================
// 辅助：根据 HANDLE 查文件路径
// ================================================================
static void GetPathFromHandle(HANDLE hFile, wchar_t* buf, DWORD bufChars) {
    buf[0] = L'\0';
    if (hFile == INVALID_HANDLE_VALUE || hFile == nullptr) return;
    GetFinalPathNameByHandleW(hFile, buf, bufChars,
        FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
}

// ================================================================
// Hook 实现
// ================================================================

HANDLE WINAPI Hook_CreateFileW(
    LPCWSTR lpFileName, DWORD dwDesiredAccess, DWORD dwShareMode,
    LPSECURITY_ATTRIBUTES lpSA, DWORD dwCreationDisposition,
    DWORD dwFlagsAndAttributes, HANDLE hTemplateFile)
{
    HANDLE h = Real_CreateFileW(lpFileName, dwDesiredAccess, dwShareMode,
        lpSA, dwCreationDisposition,
        dwFlagsAndAttributes, hTemplateFile);
    LogWrite("CreateFileW", lpFileName, dwDesiredAccess,
        (h != INVALID_HANDLE_VALUE), h);
    return h;
}

BOOL WINAPI Hook_ReadFile(
    HANDLE hFile, LPVOID lpBuffer, DWORD nBytesToRead,
    LPDWORD lpBytesRead, LPOVERLAPPED lpOverlapped)
{
    BOOL ret = Real_ReadFile(hFile, lpBuffer, nBytesToRead,
        lpBytesRead, lpOverlapped);
    wchar_t path[MAX_PATH] = {};
    GetPathFromHandle(hFile, path, MAX_PATH);
    LogWrite("ReadFile", path, GENERIC_READ, ret);
    return ret;
}

BOOL WINAPI Hook_WriteFile(
    HANDLE hFile, LPCVOID lpBuffer, DWORD nBytesToWrite,
    LPDWORD lpBytesWritten, LPOVERLAPPED lpOverlapped)
{
    BOOL ret = Real_WriteFile(hFile, lpBuffer, nBytesToWrite,
        lpBytesWritten, lpOverlapped);
    wchar_t path[MAX_PATH] = {};
    GetPathFromHandle(hFile, path, MAX_PATH);
    LogWrite("WriteFile", path, GENERIC_WRITE, ret);
    return ret;
}

BOOL WINAPI Hook_DeleteFileW(LPCWSTR lpFileName) {
    BOOL ret = Real_DeleteFileW(lpFileName);
    LogWrite("DeleteFileW", lpFileName, DELETE, ret);
    return ret;
}

BOOL WINAPI Hook_MoveFileW(LPCWSTR lpExisting, LPCWSTR lpNew) {
    BOOL ret = Real_MoveFileW(lpExisting, lpNew);
    // 记录源路径；目标路径拼在 Path 字段后
    wchar_t combined[MAX_PATH * 2] = {};
    _snwprintf_s(combined, _countof(combined), _TRUNCATE,
        L"%s -> %s", lpExisting, lpNew);
    LogWrite("MoveFileW", combined, GENERIC_WRITE, ret);
    return ret;
}

BOOL WINAPI Hook_CopyFileW(LPCWSTR lpSrc, LPCWSTR lpDst, BOOL bFailIfExists) {
    BOOL ret = Real_CopyFileW(lpSrc, lpDst, bFailIfExists);
    wchar_t combined[MAX_PATH * 2] = {};
    _snwprintf_s(combined, _countof(combined), _TRUNCATE,
        L"%s -> %s", lpSrc, lpDst);
    LogWrite("CopyFileW", combined, GENERIC_WRITE, ret);
    return ret;
}

// ================================================================
// 安装 / 卸载
// ================================================================
static void InstallHooks() {
    DetourTransactionBegin();
    DetourUpdateThread(GetCurrentThread());
    DetourAttach(&(PVOID&)Real_CreateFileW, Hook_CreateFileW);
    DetourAttach(&(PVOID&)Real_ReadFile, Hook_ReadFile);
    DetourAttach(&(PVOID&)Real_WriteFile, Hook_WriteFile);
    DetourAttach(&(PVOID&)Real_DeleteFileW, Hook_DeleteFileW);
    DetourAttach(&(PVOID&)Real_MoveFileW, Hook_MoveFileW);
    DetourAttach(&(PVOID&)Real_CopyFileW, Hook_CopyFileW);
    DetourTransactionCommit();
}

static void UninstallHooks() {
    DetourTransactionBegin();
    DetourUpdateThread(GetCurrentThread());
    DetourDetach(&(PVOID&)Real_CreateFileW, Hook_CreateFileW);
    DetourDetach(&(PVOID&)Real_ReadFile, Hook_ReadFile);
    DetourDetach(&(PVOID&)Real_WriteFile, Hook_WriteFile);
    DetourDetach(&(PVOID&)Real_DeleteFileW, Hook_DeleteFileW);
    DetourDetach(&(PVOID&)Real_MoveFileW, Hook_MoveFileW);
    DetourDetach(&(PVOID&)Real_CopyFileW, Hook_CopyFileW);
    DetourTransactionCommit();
}

// ================================================================
// DllMain
// ================================================================
BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID) {
    switch (reason) {
    case DLL_PROCESS_ATTACH:
        DisableThreadLibraryCalls(hModule);
        CreateDirectoryA("C:\\Temp", nullptr);
        if (!LoggerInit("C:\\Temp\\behavior_monitor.log")) {
            MessageBoxA(nullptr, "LoggerInit failed!", "HookDll", MB_OK);
        }
        MessageBoxA(nullptr, "Before InstallHooks", "HookDll", MB_OK); // ← 加
        InstallHooks();
        MessageBoxA(nullptr, "After InstallHooks", "HookDll", MB_OK);  // ← 加
        break;
    case DLL_PROCESS_DETACH:
        UninstallHooks();
        LoggerClose();
        break;
    }
    return TRUE;
}