include $(TOPDIR)/rules.mk

PKG_NAME:=usocket
PKG_VERSION:=0.1
PKG_RELEASE:=1

PKG_BUILD_DIR:=$(BUILD_DIR)/usocket

include $(INCLUDE_DIR)/package.mk

define Package/usocket
  SECTION:=base
  CATEGORY:=Network
  TITLE:=UnixSocket/ttys-ConsoleTool to be Called from ssh
  URL:=http://www.realraum.at/
endef

define Build/Prepare
	svn export --force https://svn.spreadspace.org/realraum/serial_console $(PKG_BUILD_DIR)
endef

define Build/Configure
endef

define Package/usocket/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/serial $(1)/usr/bin/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/usocket $(1)/usr/bin/
endef

$(eval $(call BuildPackage,usocket))
