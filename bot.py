import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# ============================================
TOKEN = "8670158841:AAEjW_2Vcx_cNpwpA_iE0dLOErfJw7Sd534"  # <--- TU TOKEN
PROPIETARIO_ID = 8651211925  # <--- TU ID
# ============================================

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados para las conversaciones
(AGREGAR_USUARIO_ID, AGREGAR_USUARIO_CREDITOS, 
 AGREGAR_CUENTA_CORREO, AGREGAR_CUENTA_CONTRASENA, AGREGAR_CUENTA_PAIS, AGREGAR_CUENTA_PLAN,
 RECARGAR_CREDITOS_ID, RECARGAR_CREDITOS_CANTIDAD,
 ELIMINAR_USUARIO_ID, CONFIRMAR_ELIMINACION) = range(10)

# Archivos JSON (SOLO HBO)
ARCHIVOS = {
    'hbo': 'hbo.json',
    'admin': 'admin.json',
    'users': 'users.json',
    'entregas': 'entregas.json'
}

# Precio HBO (5 créditos)
PRECIO_HBO = 5

# Inicializar archivos
def inicializar_archivos():
    for archivo in ARCHIVOS.values():
        if not os.path.exists(archivo):
            if archivo == 'admin.json':
                with open(archivo, 'w') as f:
                    json.dump([PROPIETARIO_ID], f)
                print(f"✅ Archivo {archivo} creado con tu ID")
            elif archivo == 'users.json':
                with open(archivo, 'w') as f:
                    json.dump({}, f)
                print(f"✅ Archivo {archivo} creado")
            elif archivo == 'entregas.json':
                with open(archivo, 'w') as f:
                    json.dump([], f)
                print(f"✅ Archivo {archivo} creado")
            else:
                with open(archivo, 'w') as f:
                    json.dump([], f)
                print(f"✅ Archivo {archivo} creado")

# Verificar si es admin
def es_admin(user_id):
    try:
        with open('admin.json', 'r') as f:
            admins = json.load(f)
        return user_id in admins
    except:
        return False

# Verificar si es propietario
def es_propietario(user_id):
    return user_id == PROPIETARIO_ID

# Verificar si es VIP (tiene créditos)
def es_vip(user_id):
    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
        return str(user_id) in users and users[str(user_id)]['creditos'] > 0
    except:
        return False

# Obtener créditos
def obtener_creditos(user_id):
    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
        return users.get(str(user_id), {}).get('creditos', 0)
    except:
        return 0

# Verificar stock HBO
def verificar_stock_hbo():
    try:
        with open('hbo.json', 'r') as f:
            cuentas = json.load(f)
        return len(cuentas)
    except:
        return 0

# Registrar entrega
def registrar_entrega(user_id, user_name, cuenta):
    try:
        with open('entregas.json', 'r') as f:
            entregas = json.load(f)
        
        registro = {
            'user_id': user_id,
            'user_name': user_name,
            'plataforma': 'HBO MAX',
            'correo': cuenta['correo'],
            'contraseña': cuenta['contraseña'],
            'pais': cuenta['pais'],
            'plan': cuenta['plan'],
            'fecha': str(datetime.now()),
            'creditos_gastados': PRECIO_HBO
        }
        
        entregas.append(registro)
        
        with open('entregas.json', 'w') as f:
            json.dump(entregas, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error registrando entrega: {e}")
        return False

# Obtener últimas entregas
def obtener_ultimas_entregas(user_id, limite=3):
    try:
        with open('entregas.json', 'r') as f:
            entregas = json.load(f)
        
        entregas_usuario = [e for e in entregas if e['user_id'] == user_id]
        return entregas_usuario[-limite:] if entregas_usuario else []
    except:
        return []

# ==================== COMANDOS ====================

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name if user.first_name else "Usuario"
    
    welcome_message = f"""
╔══════════════════════════════╗
║      🔥 HITSCOL HBO 🔥        ║
╚══════════════════════════════╝

🔰 BIENVENIDO, {user_name.upper()}

🎬 PLATAFORMA: HBO MAX
💰 COSTO: 5 CRÉDITOS

📦 PAQUETES DISPONIBLES:
• 50 CRÉDITOS → 5000 COP
• 120 CRÉDITOS → 10000 COP
• 300 CRÉDITOS → 15000 COP

⚡ COMANDOS:
/cmd - Ver todos los comandos
/comprar - Comprar créditos
/sacarcuenta - Obtener HBO MAX
"""
    await update.message.reply_text(welcome_message)

# /cmd
async def cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    comandos_basicos = """
📟 COMANDOS DISPONIBLES:

🔹 PÚBLICOS:
/start - Iniciar bot
/cmd - Este menú
/id - Tu ID
/comprar - Comprar créditos
/sellers - Contactar vendedores

🔸 VIP:
/sacarcuenta - Obtener HBO MAX
/status - Ver mi estado
/misentregas - Mi historial
"""
    
    comandos_admin = """
🔹 ADMIN:
/agregar_usuario - Agregar usuario
/recargar_creditos - Recargar créditos
/agregar_cuenta - Agregar cuenta HBO
/eliminar_usuario - Eliminar usuario
/ver_usuarios - Ver usuarios
/ver_cuentas - Ver stock
/ver_entregas - Ver entregas
/ver_cuenta_entregada - Ver detalles
"""
    
    if es_propietario(user_id) or es_admin(user_id):
        mensaje = comandos_basicos + comandos_admin
    elif es_vip(user_id):
        mensaje = comandos_basicos
    else:
        mensaje = comandos_basicos
    
    await update.message.reply_text(mensaje)

# /id
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 TU ID: `{user_id}`", parse_mode=ParseMode.MARKDOWN)

# /comprar
async def comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = """
💰 PAQUETES DE CRÉDITOS:

🎯 50 CRÉDITOS → 5000 COP
🎯 120 CRÉDITOS → 10000 COP
🎯 300 CRÉDITOS → 15000 COP

📞 CONTACTA A LOS VENDEDORES:
/sellers
"""
    await update.message.reply_text(mensaje)

# /sellers
async def sellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = """
👥 VENDEDORES AUTORIZADOS:

@Guuason - Nequi/Binance
@El_krat0s - Nequi/Binance
@F3NIS - Nequi/Binance

⚠️ SOLO COMPRAR CON ELLOS
"""
    await update.message.reply_text(mensaje)

# /status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Usuario"
    
    if not es_vip(user_id):
        await update.message.reply_text("❌ No tienes créditos. Usa /comprar")
        return
    
    creditos = obtener_creditos(user_id)
    ultimas = obtener_ultimas_entregas(user_id, 3)
    
    mensaje = f"""
📊 ESTADO DE {user_name}:

💰 CRÉDITOS: {creditos}

📋 ÚLTIMAS EXTRACCIONES:
"""
    
    if ultimas:
        for e in ultimas:
            mensaje += f"""
🎬 HBO MAX
📧 {e['correo']}
📅 {e['fecha'][:19]}
"""
    else:
        mensaje += "\n📭 Sin extracciones"
    
    await update.message.reply_text(mensaje)

# /misentregas
async def mis_entregas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        with open('entregas.json', 'r') as f:
            entregas = json.load(f)
        
        mis_entregas = [e for e in entregas if e['user_id'] == user_id]
        
        if not mis_entregas:
            await update.message.reply_text("📭 No tienes entregas registradas")
            return
        
        mensaje = "📋 HISTORIAL COMPLETO:\n\n"
        for e in mis_entregas:
            mensaje += f"""
🎬 HBO MAX
📧 {e['correo']}
🔑 {e['contraseña']}
📅 {e['fecha'][:19]}
{'='*30}
"""
        
        await update.message.reply_text(mensaje)
    except:
        await update.message.reply_text("❌ Error al obtener historial")

# /sacarcuenta
async def sacarcuenta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not es_vip(user_id):
        await update.message.reply_text("❌ No tienes créditos. Usa /comprar")
        return
    
    creditos = obtener_creditos(user_id)
    stock = verificar_stock_hbo()
    
    if creditos < PRECIO_HBO:
        await update.message.reply_text(f"❌ Créditos insuficientes\nNecesitas: {PRECIO_HBO}\nTienes: {creditos}")
        return
    
    if stock <= 0:
        await update.message.reply_text("❌ Sin stock de HBO MAX\nPronto agregaremos más")
        return
    
    try:
        with open('hbo.json', 'r') as f:
            cuentas = json.load(f)
        
        cuenta = cuentas.pop(0)
        
        with open('hbo.json', 'w') as f:
            json.dump(cuentas, f)
        
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        users[str(user_id)]['creditos'] -= PRECIO_HBO
        
        with open('users.json', 'w') as f:
            json.dump(users, f)
        
        registrar_entrega(user_id, update.effective_user.first_name or "Usuario", cuenta)
        
        mensaje = f"""
✅ EXTRACCIÓN EXITOSA

🎬 HBO MAX
📧 {cuenta['correo']}
🔑 {cuenta['contraseña']}
🌍 {cuenta['pais']}
📺 {cuenta['plan']}

💰 Créditos restantes: {users[str(user_id)]['creditos']}

⚠️ No cambiar la contraseña
"""
        await update.message.reply_text(mensaje)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ==================== ADMIN ====================

# /agregar_usuario
async def agregar_usuario_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return ConversationHandler.END
    
    await update.message.reply_text("📝 ID del usuario:")
    return AGREGAR_USUARIO_ID

async def agregar_usuario_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['target_id'] = int(update.message.text)
        await update.message.reply_text("💰 Créditos a asignar:")
        return AGREGAR_USUARIO_CREDITOS
    except:
        await update.message.reply_text("❌ ID inválido")
        return AGREGAR_USUARIO_ID

async def agregar_usuario_creditos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        creditos = int(update.message.text)
        target_id = context.user_data['target_id']
        
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        users[str(target_id)] = {
            'creditos': creditos,
            'fecha_registro': str(datetime.now())
        }
        
        with open('users.json', 'w') as f:
            json.dump(users, f)
        
        await update.message.reply_text(f"✅ Usuario {target_id} agregado con {creditos} créditos")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END

# /recargar_creditos
async def recargar_creditos_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return ConversationHandler.END
    
    await update.message.reply_text("📝 ID del usuario:")
    return RECARGAR_CREDITOS_ID

async def recargar_creditos_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['target_id'] = int(update.message.text)
        await update.message.reply_text("💰 Créditos a recargar:")
        return RECARGAR_CREDITOS_CANTIDAD
    except:
        await update.message.reply_text("❌ ID inválido")
        return RECARGAR_CREDITOS_ID

async def recargar_creditos_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cantidad = int(update.message.text)
        target_id = context.user_data['target_id']
        
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        if str(target_id) in users:
            users[str(target_id)]['creditos'] += cantidad
        else:
            users[str(target_id)] = {
                'creditos': cantidad,
                'fecha_registro': str(datetime.now())
            }
        
        with open('users.json', 'w') as f:
            json.dump(users, f)
        
        await update.message.reply_text(f"✅ {cantidad} créditos recargados a {target_id}")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END

# /agregar_cuenta
async def agregar_cuenta_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return ConversationHandler.END
    
    await update.message.reply_text("📧 Correo de HBO MAX:")
    return AGREGAR_CUENTA_CORREO

async def agregar_cuenta_correo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['correo'] = update.message.text
    await update.message.reply_text("🔑 Contraseña:")
    return AGREGAR_CUENTA_CONTRASENA

async def agregar_cuenta_contrasena(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contrasena'] = update.message.text
    await update.message.reply_text("🌍 País:")
    return AGREGAR_CUENTA_PAIS

async def agregar_cuenta_pais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pais'] = update.message.text
    await update.message.reply_text("📺 Plan:")
    return AGREGAR_CUENTA_PLAN

async def agregar_cuenta_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open('hbo.json', 'r') as f:
            cuentas = json.load(f)
        
        nueva_cuenta = {
            'correo': context.user_data['correo'],
            'contraseña': context.user_data['contrasena'],
            'pais': context.user_data['pais'],
            'plan': context.user_data['plan']
        }
        
        cuentas.append(nueva_cuenta)
        
        with open('hbo.json', 'w') as f:
            json.dump(cuentas, f)
        
        await update.message.reply_text(f"✅ Cuenta HBO agregada\nStock actual: {len(cuentas)}")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END

# /eliminar_usuario
async def eliminar_usuario_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return ConversationHandler.END
    
    await update.message.reply_text("🗑️ ID del usuario a eliminar:")
    return ELIMINAR_USUARIO_ID

async def eliminar_usuario_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text)
        
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        if str(target_id) not in users:
            await update.message.reply_text("❌ Usuario no existe")
            return ConversationHandler.END
        
        context.user_data['eliminar_id'] = target_id
        
        keyboard = [
            [InlineKeyboardButton("✅ SI", callback_data="conf_si"),
             InlineKeyboardButton("❌ NO", callback_data="conf_no")]
        ]
        
        await update.message.reply_text(
            f"¿Eliminar usuario {target_id}?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CONFIRMAR_ELIMINACION
        
    except:
        await update.message.reply_text("❌ ID inválido")
        return ELIMINAR_USUARIO_ID

async def eliminar_usuario_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "conf_si":
        target_id = context.user_data['eliminar_id']
        
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        del users[str(target_id)]
        
        with open('users.json', 'w') as f:
            json.dump(users, f)
        
        await query.edit_message_text(f"✅ Usuario {target_id} eliminado")
    else:
        await query.edit_message_text("✅ Cancelado")
    
    return ConversationHandler.END

# /ver_usuarios
async def ver_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return
    
    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        if not users:
            await update.message.reply_text("📭 No hay usuarios")
            return
        
        mensaje = "👥 USUARIOS:\n"
        total_creditos = 0
        
        for uid, data in users.items():
            mensaje += f"\n🆔 {uid}\n💰 {data['creditos']} créditos\n📅 {data.get('fecha_registro', 'N/A')[:19]}\n"
            total_creditos += data['creditos']
        
        mensaje += f"\n📊 Total créditos: {total_creditos}"
        await update.message.reply_text(mensaje)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# /ver_cuentas
async def ver_cuentas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return
    
    stock = verificar_stock_hbo()
    emoji = "✅" if stock > 0 else "❌"
    await update.message.reply_text(f"{emoji} HBO MAX: {stock} cuentas\n💰 Precio: {PRECIO_HBO} créditos")

# /ver_entregas
async def ver_entregas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return
    
    try:
        with open('entregas.json', 'r') as f:
            entregas = json.load(f)
        
        if not entregas:
            await update.message.reply_text("📭 No hay entregas")
            return
        
        mensaje = "📋 ÚLTIMAS 10 ENTREGAS:\n"
        for e in entregas[-10:]:
            mensaje += f"""
👤 {e['user_name']} (ID: {e['user_id']})
📧 {e['correo']}
🔑 {e['contraseña']}
📅 {e['fecha'][:19]}
{'='*30}
"""
        
        await update.message.reply_text(mensaje)
    except:
        await update.message.reply_text("❌ Error")

# /ver_cuenta_entregada
async def ver_cuenta_entregada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usa: /ver_cuenta_entregada ID")
        return
    
    try:
        target_id = int(args[0])
        
        with open('entregas.json', 'r') as f:
            entregas = json.load(f)
        
        entregas_usuario = [e for e in entregas if e['user_id'] == target_id]
        
        if not entregas_usuario:
            await update.message.reply_text(f"📭 Usuario {target_id} sin entregas")
            return
        
        mensaje = f"📋 HISTORIAL DE {target_id}:\n"
        for e in entregas_usuario:
            mensaje += f"""
📧 {e['correo']}
🔑 {e['contraseña']}
📅 {e['fecha'][:19]}
{'='*20}
"""
        
        await update.message.reply_text(mensaje)
    except:
        await update.message.reply_text("❌ Error")

# Manejador para comandos desconocidos
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Comando no válido. Usa /cmd")

# ==================== MAIN ====================

def main():
    print("=" * 50)
    print("🔥 HITSCOL HBO BOT v1.0 🔥")
    print("=" * 50)
    
    inicializar_archivos()
    
    application = Application.builder().token(TOKEN).build()
    
    # ConversationHandlers
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('agregar_usuario', agregar_usuario_start)],
        states={
            AGREGAR_USUARIO_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_usuario_id)],
            AGREGAR_USUARIO_CREDITOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_usuario_creditos)],
        },
        fallbacks=[]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('recargar_creditos', recargar_creditos_start)],
        states={
            RECARGAR_CREDITOS_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, recargar_creditos_id)],
            RECARGAR_CREDITOS_CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recargar_creditos_cantidad)],
        },
        fallbacks=[]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('agregar_cuenta', agregar_cuenta_start)],
        states={
            AGREGAR_CUENTA_CORREO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_cuenta_correo)],
            AGREGAR_CUENTA_CONTRASENA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_cuenta_contrasena)],
            AGREGAR_CUENTA_PAIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_cuenta_pais)],
            AGREGAR_CUENTA_PLAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_cuenta_plan)],
        },
        fallbacks=[]
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('eliminar_usuario', eliminar_usuario_start)],
        states={
            ELIMINAR_USUARIO_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, eliminar_usuario_id)],
            CONFIRMAR_ELIMINACION: [CallbackQueryHandler(eliminar_usuario_confirmar)],
        },
        fallbacks=[]
    ))
    
    # Comandos básicos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cmd", cmd))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("comprar", comprar))
    application.add_handler(CommandHandler("sellers", sellers))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("sacarcuenta", sacarcuenta))
    application.add_handler(CommandHandler("misentregas", mis_entregas))
    
    # Comandos admin
    application.add_handler(CommandHandler("ver_usuarios", ver_usuarios))
    application.add_handler(CommandHandler("ver_cuentas", ver_cuentas))
    application.add_handler(CommandHandler("ver_entregas", ver_entregas))
    application.add_handler(CommandHandler("ver_cuenta_entregada", ver_cuenta_entregada))
    
    # Manejador de comandos desconocidos
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    print("✅ Bot iniciado correctamente")
    print("📱 Esperando mensajes...")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido")
    except Exception as e:
        print(f"\n❌ Error: {e}")
