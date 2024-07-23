package com.ykaridi.jsync

object Util {
    fun getJarLocation(clazz: Class<*>): String? {
        val protectionDomain = clazz.protectionDomain
        val codeSource = protectionDomain.codeSource
        val location = codeSource?.location
        return location?.toURI()?.path
    }
}