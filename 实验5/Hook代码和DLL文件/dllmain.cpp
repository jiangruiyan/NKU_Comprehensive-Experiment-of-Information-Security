#include <windows.h>
#include <detours.h>
#include <fstream>
#include <sstream>
#include <string>
#include <iomanip>

#pragma comment(lib, "detours.lib")

// 原始 MessageBoxW 函数指针
static int (WINAPI* TrueMessageBoxW)(
    HWND hWnd,
    LPCWSTR lpText,
    LPCWSTR lpCaption,
    UINT uType
    ) = MessageBoxW;

// 简单日志函数
void WriteLog(const std::wstring& text)
{
    SYSTEMTIME st;
    GetLocalTime(&st);

    DWORD pid = GetCurrentProcessId();
    DWORD tid = GetCurrentThreadId();

    std::wofstream log;
    log.open(L"C:\\Users\\Lenovo\\Desktop\\api_hook_log.txt", std::ios::app);

    if (log.is_open()) {
        log << L"["
            << std::setw(2) << std::setfill(L'0') << st.wHour << L":"
            << std::setw(2) << std::setfill(L'0') << st.wMinute << L":"
            << std::setw(2) << std::setfill(L'0') << st.wSecond << L"."
            << std::setw(3) << std::setfill(L'0') << st.wMilliseconds
            << L"] ";

        log << L"[PID:" << pid << L"] ";
        log << L"[TID:" << tid << L"] ";

        log << text << std::endl;
        log.close();
    }
}

// Hook 后的新函数
int WINAPI MyMessageBoxW(
    HWND hWnd,
    LPCWSTR lpText,
    LPCWSTR lpCaption,
    UINT uType
)
{
    std::wstringstream ss;

    ss << L"========== MessageBoxW CALL ==========";
    WriteLog(ss.str());

    ss.str(L"");
    ss << L"HWND      : 0x" << std::hex << (uintptr_t)hWnd;
    WriteLog(ss.str());

    ss.str(L"");
    ss << L"lpText    : " << (lpText ? lpText : L"(null)");
    WriteLog(ss.str());

    ss.str(L"");
    ss << L"lpCaption : " << (lpCaption ? lpCaption : L"(null)");
    WriteLog(ss.str());

    ss.str(L"");
    ss << L"uType     : 0x" << std::hex << uType;
    WriteLog(ss.str());

    // 调用原函数
    int ret = TrueMessageBoxW(hWnd, lpText, lpCaption, uType);

    ss.str(L"");
    ss << L"Return    : " << ret;
    WriteLog(ss.str());

    WriteLog(L"=====================================");

    return ret;
}

// 安装 Hook
void AttachHooks()
{
    DetourTransactionBegin();
    DetourUpdateThread(GetCurrentThread());

    DetourAttach(
        reinterpret_cast<PVOID*>(&TrueMessageBoxW),
        MyMessageBoxW
    );

    DetourTransactionCommit();
}

// 卸载 Hook
void DetachHooks()
{
    DetourTransactionBegin();
    DetourUpdateThread(GetCurrentThread());

    DetourDetach(
        reinterpret_cast<PVOID*>(&TrueMessageBoxW),
        MyMessageBoxW
    );

    DetourTransactionCommit();
}

BOOL APIENTRY DllMain(
    HMODULE hModule,
    DWORD ul_reason_for_call,
    LPVOID lpReserved
)
{
    switch (ul_reason_for_call) {
    case DLL_PROCESS_ATTACH:
        DisableThreadLibraryCalls(hModule);
        AttachHooks();
        break;

    case DLL_PROCESS_DETACH:
        DetachHooks();
        break;
    }

    return TRUE;
}