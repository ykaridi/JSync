package com.ykaridi.jsync

import jadx.api.plugins.JadxPlugin
import jadx.api.plugins.JadxPluginContext
import jadx.api.plugins.JadxPluginInfo
import org.python.util.PythonInterpreter
import org.slf4j.LoggerFactory
import java.nio.file.Paths
import kotlin.io.path.exists


class JSyncPlugin : JadxPlugin {
    private val logger = LoggerFactory.getLogger(JSyncPlugin::class.java)
    private val uri = Util.getJarLocation(JSyncPlugin::class.java)!!

    override fun getPluginInfo(): JadxPluginInfo {
        logger.info("[JSync] loading from <$uri>")
        return JadxPluginInfo(PLUGIN_ID, "JSync",
            "Synchronization of symbols across multiple users")
    }

    override fun init(context: JadxPluginContext) {
        logger.info("[JSync] Initializing...")
        val guiContext = context.guiContext
        guiContext?.addMenuAction("JSync") {
            val interpreter = PythonInterpreter()
            interpreter[PYTHON_JADX_CONTEXT] = context

            val sourcesLocation = Paths.get(uri).toRealPath().parent.parent.parent
            val debug = sourcesLocation.resolve("DEBUG_ME").exists()

            interpreter[PYTHON_IMPORT_PATH] = if (debug) {
                sourcesLocation.resolve("src/main/python").toString()
            } else "$uri/python_code"
            interpreter[PYTHON_LOGGER] = logger
            interpreter.exec(("""
            |import sys
            |$PYTHON_LOGGER.error("[JSync] Loading python code from %s" % $PYTHON_IMPORT_PATH)
            |sys.path.append($PYTHON_IMPORT_PATH)
            |""" + (if (debug) """
            |to_pop = []
            |for name in sys.modules:
            |   if any(x in name for x in ['java_common', 'client_base', 'common', 'jsync_jadx']):
            |       to_pop.append(name)
            |
            |for name in to_pop:
            |   sys.modules.pop(name)
            |""" else "") + """
            |from jsync_jadx.plugin import run as run_jsync
            |run_jsync($PYTHON_JADX_CONTEXT, $PYTHON_LOGGER)
            """).trimMargin())
        }
    }

    companion object {
        const val PLUGIN_ID: String = "JSync"
        const val PYTHON_JADX_CONTEXT: String = "context"
        const val PYTHON_LOGGER: String = "logger"
        const val PYTHON_IMPORT_PATH: String = "import_path"
    }
}