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
import threading
from flask import Flask, jsonify

# ============================================
TOKEN = "8670158841:AAEjW_2Vcx_cNpwpA_iE0dLOErfJw7Sd534"  # <--- TU TOKEN
PROPIETARIO_ID = 8651211925  # <--- TU ID

# ============= CONFIGURACIÓN JSONbin.io =============
# Esta es tu X-Access-Key (no X-Master-Key)
JSONBIN_ACCESS_KEY = "$2a$10$/0rI1RfcE9DerLvjxUSdluCDeYK/ib9fKpEqndhnQB6OUqfUcIf1y"

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

# ============= FUNCIONES PARA JSONbin.io CON X-Access-Key =============

def leer_json_bin(bin_id):
    """Leer datos de JSONbin.io usando X-Access-Key"""
    try:
        url = f"https://api.jsonbin.io/v3/b/{bin_id}/latest"
        headers = {
            'X-Access-Key': JSONBIN_ACCESS_KEY,  # Cambiado de X-Master-Key a X-Access-Key
            'X-Bin-Meta': 'false'
        }
        print(f"📡 Leyendo bin {bin_id}...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Datos leídos correctamente de {bin_id}")
            return data
        elif response.status_code == 403:
            print(f"❌ Error 403: Acceso denegado. Verifica tu X-Access-Key")
            return None
        elif response.status_code == 404:
            print(f"❌ Error 404: Bin {bin_id} no encontrado")
            return None
        else:
            print(f"❌ Error leyendo bin {bin_id}: Código {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
    except requests.exceptions.Timeout:
        print(f"❌ Timeout leyendo bin {bin_id}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"❌ Error de conexión leyendo bin {bin_id}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None

def guardar_json_bin(bin_id, datos):
    """Guardar datos en JSONbin.io usando X-Access-Key"""
    try:
        url = f"https://api.jsonbin.io/v3/b/{bin_id}"
        headers = {
            'Content-Type': 'application/json',
            'X-Access-Key': JSONBIN_ACCESS_KEY,  # Cambiado de X-Master-Key a X-Access-Key
            'X-Bin-Versioning': 'false'
        }
        print(f"📡 Guardando en bin {bin_id}...")
        response = requests.put(url, json=datos, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Datos guardados correctamente en {bin_id}")
            return True
        elif response.status_code == 403:
            print(f"❌ Error 403: Acceso denegado. Verifica tu X-Access-Key")
            return False
        elif response.status_code == 404:
            print(f"❌ Error 404: Bin {bin_id} no encontrado")
            return False
        else:
            print(f"❌ Error guardando en bin {bin_id}: Código {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print(f"❌ Timeout guardando en bin {bin_id}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Error de conexión guardando en bin {bin_id}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def inicializar_bins():
    """Inicializar todos los bins con datos por defecto"""
    
    print("\n" + "=" * 50)
    print("🔌 CONECTANDO CON JSONbin.io")
    print("=" * 50)
    
    # Probar conexión con un bin
    test_data = leer_json_bin(BINS['admin'])
    if test_data is None:
        print("⚠️  No se pudo conectar con JSONbin.io")
        print("⚠️  Verifica tu X-Access-Key y los IDs de los bins")
        print("=" * 50)
        return False
    
    # Inicializar admin.json (LISTA)
    admin_data = leer_json_bin(BINS['admin'])
    if admin_data is None:
        admin_data = [PROPIETARIO_ID]
        if guardar_json_bin(BINS['admin'], admin_data):
            print("✅ Bin admin.json inicializado")
    else:
        print(f"✅ Bin admin.json cargado: {admin_data}")
    
    # Inicializar users.json (DICCIONARIO)
    users_data = leer_json_bin(BINS['users'])
    if users_data is None:
        users_data = {}
        if guardar_json_bin(BINS['users'], users_data):
            print("✅ Bin users.json inicializado")
    else:
        print(f"✅ Bin users.json cargado: {len(users_data)} usuarios")
    
    # Inicializar entregas.json (LISTA)
    entregas_data = leer_json_bin(BINS['entregas'])
    if entregas_data is None:
        entregas_data = []
        if guardar_json_bin(BINS['entregas'], entregas_data):
            print("✅ Bin entregas.json inicializado")
    else:
        print(f"✅ Bin entregas.json cargado: {len(entregas_data)} entregas")
    
    # Inicializar hbo.json (LISTA)
    hbo_data = leer_json_bin(BINS['hbo'])
    if hbo_data is None:
        hbo_data = []
        if guardar_json_bin(BINS['hbo'], hbo_data):
            print("✅ Bin hbo.json inicializado")
    else:
        print(f"✅ Bin hbo.json cargado: {len(hbo_data)} cuentas")
    
    print("=" * 50)
    return True

# ============= FUNCIONES DE ACCESO A DATOS =============

def obtener_admins():
    """Obtener lista de administradores"""
    data = leer_json_bin(BINS['admin'])
    return data if isinstance(data, list) else []

def es_admin(user_id):
    """Verificar si un usuario es admin"""
    admins = obtener_admins()
    return user_id in admins

def es_propietario(user_id):
    """Verificar si es el propietario"""
    return user_id == PROPIETARIO_ID

def obtener_usuarios():
    """Obtener diccionario de usuarios"""
    data = leer_json_bin(BINS['users'])
    return data if isinstance(data, dict) else {}

def es_vip(user_id):
    """Verificar si es usuario VIP"""
    users = obtener_usuarios()
    return str(user_id) in users and users[str(user_id)]['creditos'] > 0

def obtener_creditos(user_id):
    """Obtener créditos de un usuario"""
    users = obtener_usuarios()
    return users.get(str(user_id), {}).get('creditos', 0)

def guardar_usuario(user_id, datos):
    """Guardar un usuario específico"""
    users = obtener_usuarios()
    users[str(user_id)] = datos
    return guardar_json_bin(BINS['users'], users)

def eliminar_usuario_db(user_id):
    """Eliminar un usuario"""
    users = obtener_usuarios()
    if str(user_id) in users:
        del users[str(user_id)]
        return guardar_json_bin(BINS['users'], users)
    return False

def obtener_cuentas_hbo():
    """Obtener lista de cuentas HBO"""
    data = leer_json_bin(BINS['hbo'])
    return data if isinstance(data, list) else []

def guardar_cuentas_hbo(cuentas):
    """Guardar lista de cuentas HBO"""
    return guardar_json_bin(BINS['hbo'], cuentas)

def verificar_stock_hbo():
    """Verificar stock de HBO"""
    cuentas = obtener_cuentas_hbo()
    return len(cuentas)

def obtener_entregas():
    """Obtener lista de entregas"""
    data = leer_json_bin(BINS['entregas'])
    return data if isinstance(data, list) else []

def guardar_entregas(entregas):
    """Guardar lista de entregas"""
    return guardar_json_bin(BINS['entregas'], entregas)

def registrar_entrega(user_id, user_name, cuenta):
    """Registrar una entrega"""
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
    """Obtener últimas entregas de un usuario"""
    try:
        entregas = obtener_entregas()
        entregas_usuario = [e for e in entregas if e['user_id'] == user_id]
        return entregas_usuario[-limite:] if entregas_usuario else []
    except:
        return []

# ==================== FLASK KEEP ALIVE ====================

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "bot": "HITSCOL HBO",
        "timestamp": str(datetime.now())
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

def run_flask():
    app.run(host='0.0.0.0', port=8080)

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
    except Exception as e:
        await update.message.reply_text(f"❌ Error al obtener historial: {str(e)}")

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
                await update.message.reply_text("❌ Error al actualizar créditos en JSONbin")
        else:
            await update.message.reply_text("❌ Error al actualizar stock en JSONbin")
        
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
        target_id = str(context.user_data['target_id'])
        
        # Obtener usuarios actuales
        users = obtener_usuarios()
        
        # Agregar nuevo usuario
        users[target_id] = {
            'creditos': creditos,
            'fecha_registro': str(datetime.now())
        }
        
        # Guardar en JSONbin
        if guardar_json_bin(BINS['users'], users):
            await update.message.reply_text(f"✅ Usuario {target_id} agregado con {creditos} créditos")
        else:
            await update.message.reply_text("❌ Error al guardar en JSONbin. Verifica la conexión.")
        
        context.user_data.clear()
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
        target_id = str(context.user_data['target_id'])
        
        # Obtener usuarios
        users = obtener_usuarios()
        
        # Actualizar o crear usuario
        if target_id in users:
            users[target_id]['creditos'] += cantidad
        else:
            users[target_id] = {
                'creditos': cantidad,
                'fecha_registro': str(datetime.now())
            }
        
        # Guardar en JSONbin
        if guardar_json_bin(BINS['users'], users):
            await update.message.reply_text(f"✅ {cantidad} créditos recargados a {target_id}")
        else:
            await update.message.reply_text("❌ Error al guardar en JSONbin. Verifica la conexión.")
        
        context.user_data.clear()
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
            await update.message.reply_text("❌ Error al guardar en JSONbin. Verifica la conexión.")
        
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
        target_id = str(int(update.message.text))
        
        users = obtener_usuarios()
        
        if target_id not in users:
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
        
        users = obtener_usuarios()
        if target_id in users:
            del users[target_id]
            if guardar_json_bin(BINS['users'], users):
                await query.edit_message_text(f"✅ Usuario {target_id} eliminado")
            else:
                await query.edit_message_text("❌ Error al guardar en JSONbin")
        else:
            await query.edit_message_text("❌ Usuario no encontrado")
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
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

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
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

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
    if inicializar_bins():
        print("✅ Conexión con JSONbin.io establecida")
    else:
        print("⚠️  Problemas de conexión con JSONbin.io")
        print("⚠️  Verifica tu X-Access-Key y los IDs de los bins")
    
    # Iniciar Flask en un hilo separado
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Servidor web iniciado en puerto 8080")
    
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
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido")
    except Exception as e:
        print(f"\n❌ Error: {e}")
