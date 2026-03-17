import logging
import json
import os
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode
import io
import zipfile

# ============================================
TOKEN = "8670158841:AAEjW_2Vcx_cNpwpA_iE0dLOErfJw7Sd534"  # <--- TU TOKEN
PROPIETARIO_ID = 8651211925  # <--- TU ID

# ============= CONFIGURACIÓN JSONbin.io =============
JSONBIN_API_KEY = "$2a$10$/0rI1RfcE9DerLvjxUSdluCDeYK/ib9fKpEqndhnQB6OUqfUcIf1y"

BINS = {
    'hbo': '69b89c64b7ec241ddc751a8a',      # Bin de cuentas HBO
    'admin': '69b89bc4c3097a1dd52fc6f3',    # Bin de administradores
    'users': '69b89c94b7ec241ddc751b8b',    # Bin de usuarios VIP
    'entregas': '69b89c31b7ec241ddc751974'   # Bin de entregas
}
# ====================================================

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

# Precio HBO (5 créditos)
PRECIO_HBO = 5

# ============= FUNCIONES PARA JSONbin.io =============

def leer_json_bin(bin_id):
    """Leer datos de JSONbin.io"""
    try:
        url = f"https://api.jsonbin.io/v3/b/{bin_id}/latest"
        headers = {
            'X-Master-Key': JSONBIN_API_KEY
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()['record']
        else:
            print(f"Error leyendo bin {bin_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error en leer_json_bin: {e}")
        return None

def guardar_json_bin(bin_id, datos):
    """Guardar datos en JSONbin.io"""
    try:
        url = f"https://api.jsonbin.io/v3/b/{bin_id}"
        headers = {
            'Content-Type': 'application/json',
            'X-Master-Key': JSONBIN_API_KEY
        }
        response = requests.put(url, json=datos, headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Error en guardar_json_bin: {e}")
        return False

def inicializar_bins():
    """Inicializar todos los bins con datos por defecto"""
    
    # Inicializar admin.json
    admin_data = leer_json_bin(BINS['admin'])
    if admin_data is None:
        admin_data = [PROPIETARIO_ID]
        guardar_json_bin(BINS['admin'], admin_data)
        print("✅ Bin admin.json inicializado")
    
    # Inicializar users.json
    users_data = leer_json_bin(BINS['users'])
    if users_data is None:
        users_data = {}
        guardar_json_bin(BINS['users'], users_data)
        print("✅ Bin users.json inicializado")
    
    # Inicializar entregas.json
    entregas_data = leer_json_bin(BINS['entregas'])
    if entregas_data is None:
        entregas_data = []
        guardar_json_bin(BINS['entregas'], entregas_data)
        print("✅ Bin entregas.json inicializado")
    
    # Inicializar hbo.json
    hbo_data = leer_json_bin(BINS['hbo'])
    if hbo_data is None:
        hbo_data = []
        guardar_json_bin(BINS['hbo'], hbo_data)
        print("✅ Bin hbo.json inicializado")

# ============= FUNCIONES DE ACCESO A DATOS =============

def obtener_admins():
    data = leer_json_bin(BINS['admin'])
    return data if data else []

def es_admin(user_id):
    admins = obtener_admins()
    return user_id in admins

def es_propietario(user_id):
    return user_id == PROPIETARIO_ID

def obtener_usuarios():
    data = leer_json_bin(BINS['users'])
    return data if data else {}

def es_vip(user_id):
    users = obtener_usuarios()
    return str(user_id) in users and users[str(user_id)]['creditos'] > 0

def obtener_creditos(user_id):
    users = obtener_usuarios()
    return users.get(str(user_id), {}).get('creditos', 0)

def guardar_usuario(user_id, datos):
    users = obtener_usuarios()
    users[str(user_id)] = datos
    return guardar_json_bin(BINS['users'], users)

def eliminar_usuario_db(user_id):
    users = obtener_usuarios()
    if str(user_id) in users:
        del users[str(user_id)]
        return guardar_json_bin(BINS['users'], users)
    return False

def obtener_cuentas_hbo():
    data = leer_json_bin(BINS['hbo'])
    return data if data else []

def guardar_cuentas_hbo(cuentas):
    return guardar_json_bin(BINS['hbo'], cuentas)

def verificar_stock_hbo():
    cuentas = obtener_cuentas_hbo()
    return len(cuentas)

def obtener_entregas():
    data = leer_json_bin(BINS['entregas'])
    return data if data else []

def guardar_entregas(entregas):
    return guardar_json_bin(BINS['entregas'], entregas)

def registrar_entrega(user_id, user_name, cuenta):
    try:
        entregas = obtener_entregas()
        
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
        return guardar_entregas(entregas)
    except Exception as e:
        print(f"Error registrando entrega: {e}")
        return False

def obtener_ultimas_entregas(user_id, limite=3):
    try:
        entregas = obtener_entregas()
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
💰 COSTO POR CUENTA: 5 CRÉDITOS

📦 PAQUETES DISPONIBLES:
• 80 CRÉDITOS → 5000 COP / 1.63 USD
• 200 CRÉDITOS → 10000 COP / 2.90 USD

💬 ¿QUIERES MENOS O MÁS CANTIDAD?
   CONTACTA A LOS SELLERS CON /sellers

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
/exportar - Exportar todos los datos
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

🎯 80 CRÉDITOS → 5000 COP / 1.63 USD
🎯 200 CRÉDITOS → 10000 COP / 2.90 USD

💬 ¿NECESITAS OTRA CANTIDAD?
   Contáctanos directamente con /sellers
   Podemos ofrecerte paquetes personalizados

📞 VENDEDORES: /sellers
"""
    await update.message.reply_text(mensaje)

# /sellers
async def sellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = """
👥 VENDEDORES AUTORIZADOS:

@Guuason - Nequi/Binance
@El_krat0s - Nequi/Binance
@F3NIS - Nequi/Binance

💬 CONTÁCTALOS PARA:
• Comprar créditos
• Paquetes personalizados
• Menor o mayor cantidad
• Consultas y soporte

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
        entregas = obtener_entregas()
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
    cuentas = obtener_cuentas_hbo()
    stock = len(cuentas)
    
    if creditos < PRECIO_HBO:
        await update.message.reply_text(f"❌ Créditos insuficientes\nNecesitas: {PRECIO_HBO}\nTienes: {creditos}")
        return
    
    if stock <= 0:
        await update.message.reply_text("❌ Sin stock de HBO MAX\nPronto agregaremos más")
        return
    
    try:
        cuenta = cuentas.pop(0)
        
        if guardar_cuentas_hbo(cuentas):
            users = obtener_usuarios()
            users[str(user_id)]['creditos'] -= PRECIO_HBO
            
            if guardar_json_bin(BINS['users'], users):
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
            else:
                await update.message.reply_text("❌ Error al actualizar créditos")
        else:
            await update.message.reply_text("❌ Error al actualizar stock")
        
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
        
        user_data = {
            'creditos': creditos,
            'fecha_registro': str(datetime.now())
        }
        
        if guardar_usuario(target_id, user_data):
            await update.message.reply_text(f"✅ Usuario {target_id} agregado con {creditos} créditos")
        else:
            await update.message.reply_text("❌ Error al guardar usuario")
        
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
        
        users = obtener_usuarios()
        
        if str(target_id) in users:
            users[str(target_id)]['creditos'] += cantidad
        else:
            users[str(target_id)] = {
                'creditos': cantidad,
                'fecha_registro': str(datetime.now())
            }
        
        if guardar_json_bin(BINS['users'], users):
            await update.message.reply_text(f"✅ {cantidad} créditos recargados a {target_id}")
        else:
            await update.message.reply_text("❌ Error al recargar")
        
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END

# /agregar_cuenta
async def agregar_cuenta_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return ConversationHandler.END
    
    await update.message.reply_text("📧 Envíame el CORREO de HBO MAX:")
    return AGREGAR_CUENTA_CORREO

async def agregar_cuenta_correo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['correo'] = update.message.text
    await update.message.reply_text("🔑 Envíame la CONTRASEÑA:")
    return AGREGAR_CUENTA_CONTRASENA

async def agregar_cuenta_contrasena(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contrasena'] = update.message.text
    await update.message.reply_text("🌍 Envíame el PAÍS (ej: Colombia, USA, México, etc):")
    return AGREGAR_CUENTA_PAIS

async def agregar_cuenta_pais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pais'] = update.message.text
    await update.message.reply_text("📺 Envíame el PLAN (ej: Premium, Básico, Estándar, 4K, Familiar, etc):")
    return AGREGAR_CUENTA_PLAN

async def agregar_cuenta_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['plan'] = update.message.text
        
        # Verificar que todos los datos estén presentes
        if not all(k in context.user_data for k in ['correo', 'contrasena', 'pais', 'plan']):
            await update.message.reply_text("❌ Error: Faltan datos. Intenta de nuevo desde /agregar_cuenta")
            return ConversationHandler.END
        
        # Obtener cuentas actuales
        cuentas = obtener_cuentas_hbo()
        
        # Crear nueva cuenta
        nueva_cuenta = {
            'correo': context.user_data['correo'],
            'contraseña': context.user_data['contrasena'],
            'pais': context.user_data['pais'],
            'plan': context.user_data['plan']
        }
        
        # Agregar a la lista
        cuentas.append(nueva_cuenta)
        
        # Guardar
        if guardar_cuentas_hbo(cuentas):
            await update.message.reply_text(f"""
✅ CUENTA AGREGADA CON ÉXITO

📧 Correo: {context.user_data['correo']}
🔑 Contraseña: {context.user_data['contrasena']}
🌍 País: {context.user_data['pais']}
📺 Plan: {context.user_data['plan']}

📦 Stock actual: {len(cuentas)} cuentas
""")
        else:
            await update.message.reply_text("❌ Error al guardar la cuenta")
        
        # Limpiar datos temporales
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error al guardar: {str(e)}")
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
        
        users = obtener_usuarios()
        
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
        
        if eliminar_usuario_db(target_id):
            await query.edit_message_text(f"✅ Usuario {target_id} eliminado")
        else:
            await query.edit_message_text("❌ Error al eliminar")
    else:
        await query.edit_message_text("✅ Cancelado")
    
    return ConversationHandler.END

# /ver_usuarios
async def ver_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return
    
    try:
        users = obtener_usuarios()
        
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
        entregas = obtener_entregas()
        
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
        
        entregas = obtener_entregas()
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

# /exportar
async def exportar_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (es_propietario(update.effective_user.id) or es_admin(update.effective_user.id)):
        await update.message.reply_text("❌ No autorizado")
        return
    
    await update.message.reply_text("📦 Generando respaldo...")
    
    try:
        # Obtener todos los datos
        datos = {
            'hbo.json': obtener_cuentas_hbo(),
            'admin.json': obtener_admins(),
            'users.json': obtener_usuarios(),
            'entregas.json': obtener_entregas(),
            'fecha_exportacion': str(datetime.now())
        }
        
        # Crear archivo JSON
        archivo_json = json.dumps(datos, indent=2)
        
        # Enviar como documento
        await update.message.reply_document(
            document=io.BytesIO(archivo_json.encode()),
            filename=f'respaldo_hitscol_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
            caption="✅ Respaldo completo de la base de datos"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error al exportar: {str(e)}")

# Manejador para comandos desconocidos
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Comando no válido. Usa /cmd")

# ==================== MAIN ====================

def main():
    print("=" * 50)
    print("🔥 HITSCOL HBO BOT v2.0 (CON JSONbin.io) 🔥")
    print("=" * 50)
    
    # Inicializar bins en JSONbin.io
    inicializar_bins()
    
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
    application.add_handler(CommandHandler("exportar", exportar_datos))
    
    # Manejador de comandos desconocidos
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    print("✅ Bot iniciado correctamente")
    print(f"📊 Bins conectados:")
    print(f"   • Admin: {BINS['admin']}")
    print(f"   • Usuarios: {BINS['users']}")
    print(f"   • HBO: {BINS['hbo']}")
    print(f"   • Entregas: {BINS['entregas']}")
    print("📱 Esperando mensajes...")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido")
    except Exception as e:
        print(f"\n❌ Error: {e}")
