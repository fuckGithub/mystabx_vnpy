.PHONY: run-dev run-web run-web-insecure build-android build-android-dev build-ipa build-ipa-appstore build-web package package-dev test analyze format audit audit-report

run-dev:
	# 只传递环境标识，具体的 API_URL 由 main.dart 根据 ENV=dev 自动从 .env.dev 读取
	flutter run --dart-define=ENV=dev

run-web:
	flutter run -d chrome --web-port 6150 --dart-define=ENV=dev

# 本地 Web 预览跨域图片（COS 未配 CORS 时的临时绕过）：
# CanvasKit renderer 加载图片走 fetch → 受浏览器同源策略限制；
# --disable-web-security 必须配合独立 --user-data-dir 才生效（新版 Chrome 安全策略）。
# ⚠️ 副作用：独立 profile 无登录态（localStorage 隔离），需重新登录；仅用于本地调试。
run-web-insecure:
	flutter run -d chrome --web-port 6150 --dart-define=ENV=dev \
		--web-browser-flag="--disable-web-security" \
		--web-browser-flag="--user-data-dir=/tmp/flutter_chrome_insecure"

# 构建 APK：版本号由 gradle 自动从 lib/env/.env.<ENV> 读取（APP_VERSION=versionName / APP_BUILD=versionCode），
# 只需指定 ENV 即可生成对应环境+版本的包
# 产物：build/app/outputs/apk/release/{APP_NAME}-{APP_VERSION}-{APP_BUILD}-release.apk
# dev / test / prod 三个环境的包名规则一致，便于 CI/CD 自动化处理。
build-android:
	flutter build apk --release --dart-define=ENV=dev
	@echo "📦 Gradle output:" && ls -lh build/app/outputs/apk/release/*.apk 2>/dev/null || true

# 构建 iOS 分发包（ipa）：产物名与版本号均从 lib/env/.env.<ENV> 派生（对齐 Android 命名规则）
# 用法：make build-ipa                        # ENV=prod → build/ios/ipa/xxx-3.0.0-300.ipa
#      make build-ipa ENV=dev                 # dev      → build/ios/ipa/xxx-3.0.0-alpha-301.ipa
#      make build-ipa EXPORT_METHOD=app-store # TestFlight/上架导出（需 App Store 分发证书）
# ⚠️ iOS 版本号不走 gradle：必须用 --build-name/--build-number 覆盖，
#    否则 ipa 取 pubspec 3.0.0+300（与文件名不一致，dev 包会误标成 prod 版本）。
#    导出默认 development（本机仅 Apple Development 证书；ad-hoc/app-store 需分发证书）。
EXPORT_METHOD ?= development

# ⚠️ 说明：以下注释只能放在 recipe 之外（makefile 级）。
#    recipe 内的“纯注释行”会被 make 当作空行，把 recipe 拆成多个独立 shell 进程，
#    导致前面赋值的 app_name/app_ver/app_build 全部丢失（表现为 --build-name 为空、
#    回退 pubspec 版本、产物被 mv 成 --.ipa）。见 make 对 recipe 内 `#` 行的处理。
# iOS 版本号必须 x.y.z（Flutter 忽略非数字 build-name 并静默回退 pubspec）：
# 剥掉 APP_VERSION 的 -alpha/-rc 后缀作为 --build-name（文件名仍保留完整 APP_VERSION 便于识别）
build-ipa: ENV=prod
build-ipa:
	@env_file=lib/env/.env.$(ENV); \
	[ -f "$$env_file" ] || { echo "❌ 缺少 $$env_file（ENV=$(ENV)）"; exit 1; }; \
	app_name=$$(grep -E '^APP_NAME=' "$$env_file" | head -1 | cut -d= -f2); \
	app_ver=$$(grep -E '^APP_VERSION=' "$$env_file" | head -1 | cut -d= -f2); \
	app_build=$$(grep -E '^APP_BUILD=' "$$env_file" | head -1 | cut -d= -f2); \
	app_ver_ios=$$(echo "$$app_ver" | sed -E 's/-[^-]*$$//'); \
	base="$${app_name}-$${app_ver}-$${app_build}"; \
	rm -f build/ios/ipa/*.ipa; \
	flutter build ipa --release --dart-define=ENV=$(ENV) \
		--build-name="$$app_ver_ios" --build-number="$$app_build" \
		--export-method=$(EXPORT_METHOD) \
		--obfuscate --split-debug-info=build/ios/debug-info && \
	ipa_src=$$(ls build/ios/ipa/*.ipa | head -1) && \
	mv "$$ipa_src" "build/ios/ipa/$${base}.ipa" && \
	echo "✅ iOS ipa: build/ios/ipa/$${base}.ipa"

# 上架专用：app-store 导出（需 App Store 分发证书）
build-ipa-appstore:
	$(MAKE) build-ipa EXPORT_METHOD=app-store


# 一键打包（傻瓜式一条命令）：Android APK + iOS ipa，产物名由 .env 自动派生
#   make package      → 生产包：build/.../xxx-3.0.0-300-release.apk + build/ios/ipa/xxx-3.0.0-300.ipa
#   make package-dev  → 测试包：build/.../xxx-3.0.0-alpha-301-release.apk + build/ios/ipa/xxx-3.0.0-alpha-301.ipa
package: build-android build-ipa

package-dev:
	$(MAKE) build-android
	$(MAKE) build-ipa ENV=dev

package-test:
	flutter build apk --release --dart-define=ENV=test
	$(MAKE) build-ipa ENV=test

package-prod:
	flutter build apk --release --dart-define=ENV=prod
	$(MAKE) build-ipa ENV=prod

build-web:
	flutter build web --dart-define=ENV=prod

test:
	flutter test

analyze:
	flutter analyze

format:
	dart format lib test

# 依赖: dart pub global activate flutter_auditor（并将 $HOME/.pub-cache/bin 加入 PATH）
# 注: flutter_auditor 上游 main() 丢弃退出码（进程恒为 0），故用文本断言实现门禁；
#     若上游修复退出码，可回归 --fail-on high 即可。
audit:
	@out=$$(flutter_auditor audit --fail-on high 2>&1); \
	echo "$$out"; \
	echo "$$out" | grep -qE 'High Risk[[:space:]]*:[[:space:]]*[0-9]' || { \
		echo "❌ AUDIT GATE FAILED: cannot parse audit summary (flutter_auditor installed? check PATH)"; \
		exit 1; \
	}; \
	if echo "$$out" | grep -qE 'High Risk[[:space:]]*:[[:space:]]*[1-9]'; then \
		echo "❌ AUDIT GATE FAILED: high-risk findings present (see output above)"; \
		exit 1; \
	fi; \
	echo "✅ AUDIT GATE PASSED"

audit-report:
	flutter_auditor audit --html build/audit_report.html --fail-on high
