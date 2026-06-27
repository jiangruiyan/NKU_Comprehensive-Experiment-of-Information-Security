LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE    := zygisk_envoy
LOCAL_SRC_FILES := main.cpp
LOCAL_LDLIBS    := -llog -ldl
LOCAL_CFLAGS    := -Wall -O2 -fvisibility=hidden
LOCAL_CPPFLAGS  := -std=c++17
include $(BUILD_SHARED_LIBRARY)
