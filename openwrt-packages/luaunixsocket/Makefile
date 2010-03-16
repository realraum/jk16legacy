#
# Copyright (C) 2009 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

include $(TOPDIR)/rules.mk

PKG_NAME:=luaunixsocket
PKG_VERSION:=2.0.2
PKG_RELEASE:=1

PKG_SOURCE:=luasocket-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=http://luaforge.net/frs/download.php/2664
PKG_MD5SUM:=41445b138deb7bcfe97bff957503da8e

include $(INCLUDE_DIR)/package.mk

define Package/luaunixsocket
  SUBMENU:=Lua
  SECTION:=lang
  CATEGORY:=Languages
  TITLE:=LuaUnixSocket
  URL:=http://luasocket.luaforge.net/
  DEPENDS:=+luasocket
endef

define Package/luaunixsocket/description
  LuaSocket is the most comprehensive networking support
  library for the Lua language. It provides easy access to
  TCP, UDP, DNS, SMTP, FTP, HTTP, MIME and much more.
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	/bin/tar -C $(PKG_BUILD_DIR) -x --strip-components 1 -f $(DL_DIR)/$(PKG_SOURCE)
endef

define Build/Configure
endef

define Build/Compile
	$(MAKE) -C $(PKG_BUILD_DIR)/ \
		LIBDIR="$(TARGET_LDFLAGS)" \
		CC="$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) -std=gnu99" \
		LD="$(TARGET_CROSS)ld -shared" \
		all
	$(MAKE) -C $(PKG_BUILD_DIR)/src/ \
		LIBDIR="$(TARGET_LDFLAGS)" \
		CC="$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) -std=gnu99" \
		LD="$(TARGET_CROSS)ld -shared" \
		unix.so
endef


define Package/luaunixsocket/install
	$(INSTALL_DIR) $(1)/usr/lib/lua
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/unix.so $(1)/usr/lib/lua
	$(INSTALL_DIR) $(1)/usr/lib/lua/socket
	ln -sf ../unix.so $(1)/usr/lib/lua/socket/unix.so
endef

$(eval $(call BuildPackage,luaunixsocket))
