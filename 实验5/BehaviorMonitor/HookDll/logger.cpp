#include "logger.h"
#include <stdio.h>
#include <mutex>
#include <time.h>

static FILE* g_log = nullptr;
static std::mutex g_mutex;

bool LoggerInit(const char* logPath) {
    std::lock_guard<std::mutex> lock(g_mutex);
    return fopen_s(&g_log, logPath, "a") == 0;
}

void LoggerClose() {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_log) { fclose(g_log); g_log = nullptr; }
}

// 格式化访问权限
static void FormatAccess(DWORD access, char* buf, size_t bufSize) {
    buf[0] = '\0';
    if (access & GENERIC_READ)    strncat_s(buf, bufSize, "READ|", _TRUNCATE);
    if (access & GENERIC_WRITE)   strncat_s(buf, bufSize, "WRITE|", _TRUNCATE);
    if (access & GENERIC_EXECUTE) strncat_s(buf, bufSize, "EXEC|", _TRUNCATE);
    if (access & GENERIC_ALL)     strncat_s(buf, bufSize, "ALL|", _TRUNCATE);
    if (access & DELETE)          strncat_s(buf, bufSize, "DELETE|", _TRUNCATE);
    // 去掉末尾的 |
    size_t len = strlen(buf);
    if (len > 0 && buf[len - 1] == '|') buf[len - 1] = '\0';
    if (buf[0] == '\0') snprintf(buf, bufSize, "0x%08X", access);
}

void LogWrite(const char* apiFuncName,
    const wchar_t* filePath,
    DWORD desiredAccess,
    BOOL  retVal,
    HANDLE retHandle)
{
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_log) return;

    // 时间戳
    SYSTEMTIME st;
    GetLocalTime(&st);

    // PID / TID
    DWORD pid = GetCurrentProcessId();
    DWORD tid = GetCurrentThreadId();

    // 访问权限字符串
    char accessStr[128];
    FormatAccess(desiredAccess, accessStr, sizeof(accessStr));

    // 返回值字符串
    char retStr[64];
    if (retHandle != INVALID_HANDLE_VALUE) {
        snprintf(retStr, sizeof(retStr), "HANDLE=0x%p", retHandle);
    }
    else {
        snprintf(retStr, sizeof(retStr), "%s", retVal ? "TRUE" : "FALSE");
    }

    fprintf(g_log,
        "[%04d-%02d-%02d %02d:%02d:%02d.%03d] "
        "PID=%-6lu TID=%-6lu "
        "API=%-14s "
        "Access=%-24s "
        "Ret=%-24s "
        "Path=%ls\n",
        st.wYear, st.wMonth, st.wDay,
        st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
        pid, tid,
        apiFuncName,
        accessStr,
        retStr,
        filePath ? filePath : L"(null)"
    );

    fflush(g_log);
}