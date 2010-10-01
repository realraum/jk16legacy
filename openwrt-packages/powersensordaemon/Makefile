include $(TOPDIR)/rules.mk

PKG_NAME:=powersensordaemon
PKG_VERSION:=0.6
PKG_RELEASE:=1

PKG_BUILD_DIR:=$(BUILD_DIR)/powersensordaemon

include $(INCLUDE_DIR)/package.mk

define Package/powersensordaemon
  SECTION:=base
  CATEGORY:=Network
  TITLE:=RealRaum Power Sensor Daemon
  URL:=http://www.realraum.at/
endef


define Build/Prepare
	svn export --force https://svn.spreadspace.org/realraum/powersensordaemon $(PKG_BUILD_DIR)
endef


define Build/Configure
	cd $(PKG_BUILD_DIR) && ./configure --target=Linux
endef

define Package/powersensordaemon/install
	$(INSTALL_DIR) $(1)/usr/sbin
	$(INSTALL_DIR) $(1)/etc/powersensordaemon
	# produces error
	#$(INSTALL_DIR) $(1)/var/run/powersensordaemon
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/powersensordaemon $(1)/usr/sbin/powersensordaemon
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/sampledev.txt $(1)/etc/powersensordaemon/sampledev.txt
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/powerids.txt $(1)/etc/powersensordaemon/powerids.txt
endef

$(eval $(call BuildPackage,powersensordaemon))
