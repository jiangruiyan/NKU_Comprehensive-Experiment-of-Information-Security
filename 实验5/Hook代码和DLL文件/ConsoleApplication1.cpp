#include <windows.h>
#include <iostream>

int main()
{
    HMODULE hDll = LoadLibraryW(L"E:\\C++Code\\Dll1\\x64\\Debug\\Dll1.dll");

    if (!hDll) {
        std::cout << "LoadLibrary failed: " << GetLastError() << std::endl;
        return 1;
    }

    MessageBoxW(NULL, L"Hello Detours", L"Test", MB_OK);

    FreeLibrary(hDll);
    return 0;
}