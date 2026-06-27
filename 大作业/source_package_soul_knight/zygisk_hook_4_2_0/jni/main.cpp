/**
 * Soul Knight 4.2 — 古代元素使(Envoy) 技能修改 Zygisk 模块
 *
 * 构建方式: 见 build.py 或手动 ndk-build
 * 安装: 在 Magisk 中刷入生成的 zygisk_envoy_mod.zip
 *
 * 所有函数均为 ARM 模式 (非 Thumb-2), 已通过 libil2cpp.so 二进制验证
 */

#include <jni.h>
#include <cstring>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <pthread.h>
#include <dlfcn.h>
#include <unistd.h>
#include <sys/mman.h>
#include <android/log.h>

#include "zygisk.hpp"

#define TAG "EnvoyMod"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO,  TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, TAG, __VA_ARGS__)

// ========================== 配置 (修改数值) ======================

namespace Config {
    // 技能冷却 (秒), 原值 ~6-8
    static float skillCd          = 0.5f;
    // 元素塔上限, 原值 3
    static int   maxSteleCount    = 20;
    // 蓄力时间 (秒), 原值 ~2-3
    static float maxTime          = 0.5f;
    // 技能能量消耗, 原值 ~50
    static int   skillPrice       = 0;
    // 塔存活时间 (秒), 原值 ~10-15
    static float steleDeadTime    = 999.0f;
    // 索敌范围, 原值 ~5-8
    static float steleFindRange   = 20.0f;
    // 元素触发率 (%), 原值 ~30-50
    static int   elementRate      = 100;
    // 每秒恢复能量, 原值 ~1-2
    static float restoreEnergy    = 50.0f;
}

// ========================== RVA (4.2 armeabi-v7a ARM) ==========================

namespace RVA {
    // C19Controller (古代元素使主控)
    static constexpr uintptr_t C19_SetUpChar       = 0x2583758;
    // SteleController (元素塔实体)
    static constexpr uintptr_t Stele_Start         = 0x12B5DB0;
    static constexpr uintptr_t Stele_GetHurt       = 0x12B6F74;
    // SteleControllerElementAttack (元素攻击逻辑)
    static constexpr uintptr_t ElemAtk_Start       = 0xEAA708;
    static constexpr uintptr_t ElemAtk_OnHitEnemy  = 0xEAAD6C;
}

// ========================== IL2CPP 字段偏移 ==========================

namespace Off {
    // RGController
    static constexpr int skills     = 0xD4;   // List<SkillInfo>
    // C19Controller
    static constexpr int restoreEPS = 0x210;  // float restoreEnergyPerSecond
    // SkillInfo
    static constexpr int maxTime    = 0x24;
    static constexpr int maxCount   = 0x2C;
    static constexpr int cd         = 0x34;
    static constexpr int price      = 0x38;
    // SteleController
    static constexpr int strength   = 0x120;
    static constexpr int findRange  = 0x12C;
    static constexpr int deadTime   = 0x130;
    // SteleControllerElementAttack
    static constexpr int elemRate   = 0x34;
    // IL2CPP List<T>
    static constexpr int list_items = 0x8;
    static constexpr int list_size  = 0xC;
    static constexpr int arr_data   = 0x10;
}

// ========================== IL2CPP List 辅助 ==========================

static int listSize(void *list) {
    if (!list) return 0;
    return *(int *)((uint8_t *)list + Off::list_size);
}

static void *listGet(void *list, int idx) {
    if (!list) return nullptr;
    int sz = *(int *)((uint8_t *)list + Off::list_size);
    if (idx < 0 || idx >= sz) return nullptr;
    void *items = *(void **)((uint8_t *)list + Off::list_items);
    if (!items) return nullptr;
    return *(void **)((uint8_t *)items + Off::arr_data + idx * 4);
}

// ========================== ARM32 Inline Hook ==========================
//
// 所有目标函数均为 ARM 模式 (经验证)
// Hook 原理: 覆盖函数前 8 字节为 LDR PC, [PC, #-4]; <addr>
// 跳板 (trampoline): 保存原始 8 字节 + 跳回 original+8
//

static long s_page_size = 0;

static int mem_unprotect(void *addr, size_t len) {
    if (!s_page_size) s_page_size = sysconf(_SC_PAGESIZE);
    uintptr_t start = (uintptr_t)addr & ~(s_page_size - 1);
    uintptr_t end   = ((uintptr_t)addr + len + s_page_size - 1) & ~(s_page_size - 1);
    return mprotect((void *)start, end - start, PROT_READ | PROT_WRITE | PROT_EXEC);
}

static bool hook_arm(void *target, void *replacement, void **orig_out) {
    if (mem_unprotect(target, 8) != 0) {
        LOGE("mprotect failed for %p: %s", target, strerror(errno));
        return false;
    }

    // 分配跳板: 原始 8 字节 + 跳回指令 8 字节 = 16 字节
    void *tramp = mmap(nullptr, (size_t)s_page_size,
                       PROT_READ | PROT_WRITE | PROT_EXEC,
                       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (tramp == MAP_FAILED) {
        LOGE("mmap trampoline failed");
        return false;
    }

    // 1) 复制原始 8 字节到跳板
    memcpy(tramp, target, 8);

    // 2) 跳板末尾写 "跳回 target+8"
    uint32_t *back = (uint32_t *)((uint8_t *)tramp + 8);
    back[0] = 0xE51FF004;                           // LDR PC, [PC, #-4]
    back[1] = (uint32_t)((uint8_t *)target + 8);    // 跳回地址

    // 3) 在 target 写 "跳到 replacement"
    uint32_t *hook = (uint32_t *)target;
    hook[0] = 0xE51FF004;                            // LDR PC, [PC, #-4]
    hook[1] = (uint32_t)replacement;                 // 替换函数地址

    // 4) 刷新指令缓存
    __builtin___clear_cache((char *)target, (char *)target + 8);
    __builtin___clear_cache((char *)tramp,  (char *)tramp + 16);

    if (orig_out) *orig_out = tramp;

    LOGI("Hooked %p -> %p (trampoline %p)", target, replacement, tramp);
    return true;
}

// 直接 patch: 函数入口写 BX LR (ARM 模式, 立即返回)
static bool patch_return_void(void *target) {
    if (mem_unprotect(target, 4) != 0) return false;
    *(uint32_t *)target = 0xE12FFF1E;  // BX LR
    __builtin___clear_cache((char *)target, (char *)target + 4);
    LOGI("Patched BX LR at %p", target);
    return true;
}

// ========================== Hook 替换函数 ==========================

// --- C19Controller.SetUpChar() ---
typedef void (*fn_SetUpChar)(void *self);
static fn_SetUpChar orig_SetUpChar = nullptr;

static void hook_SetUpChar(void *self) {
    orig_SetUpChar(self);

    // 修改 skills 列表中的 SkillInfo
    void *skillsList = *(void **)((uint8_t *)self + Off::skills);
    int cnt = listSize(skillsList);
    LOGI("SetUpChar: skills count = %d", cnt);

    for (int i = 0; i < cnt; i++) {
        void *si = listGet(skillsList, i);
        if (!si) continue;

        float oCd   = *(float *)((uint8_t *)si + Off::cd);
        int   oMC   = *(int   *)((uint8_t *)si + Off::maxCount);
        float oMT   = *(float *)((uint8_t *)si + Off::maxTime);
        int   oPr   = *(int   *)((uint8_t *)si + Off::price);
        LOGI("  Skill[%d] BEFORE cd=%.1f maxCount=%d maxTime=%.1f price=%d",
             i, oCd, oMC, oMT, oPr);

        *(float *)((uint8_t *)si + Off::cd)       = Config::skillCd;
        *(int   *)((uint8_t *)si + Off::maxCount) = Config::maxSteleCount;
        *(float *)((uint8_t *)si + Off::maxTime)  = Config::maxTime;
        *(int   *)((uint8_t *)si + Off::price)    = Config::skillPrice;

        LOGI("  Skill[%d] AFTER  cd=%.1f maxCount=%d maxTime=%.1f price=%d",
             i, Config::skillCd, Config::maxSteleCount, Config::maxTime, Config::skillPrice);
    }

    // 修改每秒回能
    float oRestore = *(float *)((uint8_t *)self + Off::restoreEPS);
    *(float *)((uint8_t *)self + Off::restoreEPS) = Config::restoreEnergy;
    LOGI("  restoreEnergyPerSecond: %.1f -> %.1f", oRestore, Config::restoreEnergy);
}

// --- SteleController.Start() ---
typedef void (*fn_SteleStart)(void *self);
static fn_SteleStart orig_SteleStart = nullptr;

static void hook_SteleStart(void *self) {
    orig_SteleStart(self);

    float oDT = *(float *)((uint8_t *)self + Off::deadTime);
    float oFR = *(float *)((uint8_t *)self + Off::findRange);

    *(float   *)((uint8_t *)self + Off::deadTime)  = Config::steleDeadTime;
    *(float   *)((uint8_t *)self + Off::findRange) = Config::steleFindRange;
    *(uint8_t *)((uint8_t *)self + Off::strength)  = 1;

    LOGI("SteleStart: deadTime %.1f->%.1f findRange %.1f->%.1f strength->1",
         oDT, Config::steleDeadTime, oFR, Config::steleFindRange);
}

// --- SteleControllerElementAttack.Start() ---
typedef void (*fn_ElemAtkStart)(void *self);
static fn_ElemAtkStart orig_ElemAtkStart = nullptr;

static void hook_ElemAtkStart(void *self) {
    orig_ElemAtkStart(self);

    int oRate = *(int *)((uint8_t *)self + Off::elemRate);
    *(int *)((uint8_t *)self + Off::elemRate) = Config::elementRate;
    LOGI("ElemAtkStart: elementRate %d -> %d", oRate, Config::elementRate);
}

// --- SteleControllerElementAttack.OnHitEnemy(bool isCritical, RGEController* rgeCtrl) ---
typedef void (*fn_OnHitEnemy)(void *self, int isCritical, void *rgeCtrl);
static fn_OnHitEnemy orig_OnHitEnemy = nullptr;

static void hook_OnHitEnemy(void *self, int isCritical, void *rgeCtrl) {
    // 强制暴击
    orig_OnHitEnemy(self, 1, rgeCtrl);
}

// ========================== 主 Hook 安装 ==========================

static uintptr_t il2cpp_base = 0;

static uintptr_t find_il2cpp_base() {
    FILE *fp = fopen("/proc/self/maps", "r");
    if (!fp) return 0;

    char line[512];
    uintptr_t base = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "libil2cpp.so") && strstr(line, "r-xp")) {
            base = strtoul(line, nullptr, 16);
            break;
        }
    }
    fclose(fp);
    return base;
}

static void *hook_thread(void *) {
    LOGI("Hook thread started, waiting for libil2cpp.so...");

    // 等待 libil2cpp.so 加载 (最多 30 秒)
    for (int i = 0; i < 60; i++) {
        void *h = dlopen("libil2cpp.so", RTLD_NOLOAD);
        if (h) {
            dlclose(h);
            break;
        }
        usleep(500000);
    }

    il2cpp_base = find_il2cpp_base();
    if (il2cpp_base == 0) {
        LOGE("Cannot find libil2cpp.so base address!");
        return nullptr;
    }
    LOGI("libil2cpp.so base = 0x%08X", (unsigned)il2cpp_base);

    // 等待 IL2CPP 初始化完成
    usleep(3000000);

    // 安装 hooks
    hook_arm((void *)(il2cpp_base + RVA::C19_SetUpChar),
             (void *)hook_SetUpChar, (void **)&orig_SetUpChar);

    hook_arm((void *)(il2cpp_base + RVA::Stele_Start),
             (void *)hook_SteleStart, (void **)&orig_SteleStart);

    hook_arm((void *)(il2cpp_base + RVA::ElemAtk_Start),
             (void *)hook_ElemAtkStart, (void **)&orig_ElemAtkStart);

    hook_arm((void *)(il2cpp_base + RVA::ElemAtk_OnHitEnemy),
             (void *)hook_OnHitEnemy, (void **)&orig_OnHitEnemy);

    // 元素塔无敌: GetHurt 直接返回
    patch_return_void((void *)(il2cpp_base + RVA::Stele_GetHurt));

    LOGI("===== All hooks applied! Envoy Mod Active =====");
    LOGI("  cd=%.1f  maxCount=%d  maxTime=%.1f  price=%d",
         Config::skillCd, Config::maxSteleCount, Config::maxTime, Config::skillPrice);
    LOGI("  deadTime=%.0f  findRange=%.0f  elementRate=%d",
         Config::steleDeadTime, Config::steleFindRange, Config::elementRate);
    LOGI("  restoreEnergy=%.0f  forceCrit=ON  towerInvincible=ON",
         Config::restoreEnergy);
    return nullptr;
}

// ========================== Zygisk 模块 ==========================

class EnvoyModule : public zygisk::ModuleBase {
public:
    void onLoad(zygisk::Api *api, JNIEnv *env) override {
        this->api_ = api;
        this->env_ = env;
    }

    void preAppSpecialize(zygisk::AppSpecializeArgs *args) override {
        const char *name = env_->GetStringUTFChars(args->nice_name, nullptr);
        should_hook_ = (strcmp(name, "com.ChillyRoom.DungeonShooter") == 0);
        env_->ReleaseStringUTFChars(args->nice_name, name);

        if (!should_hook_) {
            api_->setOption(zygisk::DLCLOSE_MODULE_LIBRARY);
        }
    }

    void postAppSpecialize(const zygisk::AppSpecializeArgs *args) override {
        if (!should_hook_) return;

        LOGI("Soul Knight process detected, launching hook thread...");
        pthread_t tid;
        pthread_create(&tid, nullptr, hook_thread, nullptr);
        pthread_detach(tid);
    }

private:
    zygisk::Api *api_ = nullptr;
    JNIEnv      *env_ = nullptr;
    bool should_hook_  = false;
};

REGISTER_ZYGISK_MODULE(EnvoyModule)
