#include <windows.h>
#include <detours.h>
#include <stdio.h>

#pragma comment(lib, "detours.lib")

//int main(int argc, char* argv[]) {
//    if (argc < 3) {
//        printf("Usage: Launcher.exe <target.exe> <HookDll.dll> [args...]\n");
//        printf("Example: Launcher.exe C:\\Windows\\System32\\notepad.exe HookDll.dll\n");
//        return 1;
//    }
//
//    const char* targetExe = argv[1];
//    const char* dllPath = argv[2];
//
//    // 构建命令行（目标程序 + 额外参数）
//    char cmdLine[1024] = {};
//    strncpy_s(cmdLine, targetExe, _TRUNCATE);
//    for (int i = 3; i < argc; i++) {
//        strncat_s(cmdLine, " ", _TRUNCATE);
//        strncat_s(cmdLine, argv[i], _TRUNCATE);
//    }
//
//    STARTUPINFOA        si = { sizeof(si) };
//    PROCESS_INFORMATION pi = {};
//
//    const char* dlls[] = { dllPath };
//
//    printf("[*] Target : %s\n", targetExe);
//    printf("[*] DLL    : %s\n", dllPath);
//
//    // 确保日志目录存在
//    CreateDirectoryA("C:\\Temp", nullptr);
//
//    BOOL ok = DetourCreateProcessWithDllsA(
//        targetExe,          // 可执行文件路径
//        cmdLine,            // 命令行
//        nullptr,            // 进程安全属性
//        nullptr,            // 线程安全属性
//        FALSE,              // 不继承句柄
//        CREATE_NEW_CONSOLE, // 创建新控制台窗口
//        nullptr,            // 继承父进程环境变量
//        nullptr,            // 继承父进程工作目录
//        &si,
//        &pi,
//        1,                  // 注入 DLL 数量
//        dlls,
//        nullptr
//    );
//
//    if (!ok) {
//        printf("[!] Injection failed. Error: %lu\n", GetLastError());
//        return 1;
//    }
//
//    printf("[+] Target process started successfully.\n");
//    printf("[+] PID = %lu\n", pi.dwProcessId);
//    printf("[+] Log file: C:\\Temp\\behavior_monitor.log\n");
//
//    // 等待目标进程退出
//    WaitForSingleObject(pi.hProcess, INFINITE);
//
//    DWORD exitCode = 0;
//    GetExitCodeProcess(pi.hProcess, &exitCode);
//    printf("[+] Process exited with code: %lu\n", exitCode);
//
//    CloseHandle(pi.hProcess);
//    CloseHandle(pi.hThread);
//    return 0;
//}

// 把 argv 改为宽字符
int wmain(int argc, wchar_t* argv[]) {

    const wchar_t* targetExe = argv[1];
    const wchar_t* dllPath = argv[2];

    // 命令行
    wchar_t cmdLine[1024] = {};
    wcsncpy_s(cmdLine, targetExe, _TRUNCATE);

    STARTUPINFOW        si = { sizeof(si) };
    PROCESS_INFORMATION pi = {};

    const char* dllPathA[1];
    char dllBuf[MAX_PATH] = {};
    WideCharToMultiByte(CP_ACP, 0, dllPath, -1,
        dllBuf, MAX_PATH, nullptr, nullptr);
    dllPathA[0] = dllBuf;

    CreateDirectoryA("C:\\Temp", nullptr);

    BOOL ok = DetourCreateProcessWithDllsW(
        targetExe,
        cmdLine,
        nullptr, nullptr, FALSE,
        CREATE_NEW_CONSOLE,
        nullptr, nullptr,
        &si, &pi,
        1, dllPathA,
        nullptr
    );

    if (!ok) {
        wprintf(L"[!] Injection failed. Error: %lu\n", GetLastError());
        return 1;
    }

    wprintf(L"[+] Target process started successfully.\n");  // ← 确认有这行
    wprintf(L"[+] PID = %lu\n", pi.dwProcessId);
    wprintf(L"[+] Log: C:\\Temp\\behavior_monitor.log\n");

    WaitForSingleObject(pi.hProcess, INFINITE);

    DWORD exitCode = 0;
    GetExitCodeProcess(pi.hProcess, &exitCode);
    wprintf(L"[+] Process exited with code: %lu\n", exitCode);  // ← 确认有这行

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return 0;
}