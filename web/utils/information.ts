export interface InformationPage {
  title: string
  description: string
  blocks: { heading: string; text: string[] }[]
}

export const INFORMATION: Record<string, InformationPage> = {
  contacto: {
    title: 'Contacto', description: 'Cómo contactar con Foro IA al Día para consultas, correcciones y privacidad.',
    blocks: [
      { heading: 'Escríbenos', text: ['El contacto de la publicación es admin@foroiaaldia.com. Indica el asunto y, si escribes sobre un artículo, incluye su dirección y el fragmento al que te refieres. No envíes contraseñas, claves API ni documentación personal innecesaria.'] },
      { heading: 'Correcciones y derechos', text: ['Puedes comunicar errores, problemas de acceso o una posible infracción de derechos. Para corregir un dato, aporta la fuente original si la tienes. Revisaremos la solicitud; una respuesta no es inmediata ni implica aceptar automáticamente el cambio solicitado.'] }
    ]
  },
  'criterio-editorial': {
    title: 'Criterio editorial', description: 'Fuentes, uso de inteligencia artificial y correcciones en Foro IA al Día.',
    blocks: [
      { heading: 'Fuentes y alcance', text: ['Publicamos en español internacional a partir de fuentes identificadas, principalmente en inglés. La investigación consulta un registro limitado de fabricantes, comunidades, investigación y documentación oficial. Las noticias requieren corroboración independiente; los tutoriales pueden apoyarse en documentación oficial pertinente y ejemplos comprobados. No representa todas las conversaciones de Internet ni una medición de popularidad global.'] },
      { heading: 'Cómo interviene la IA', text: ['La IA puede redactar, revisar y corregir borradores. El sistema comprueba referencias, coincidencia de citas, formato y duplicados antes de decidir su publicación. Una revisión automática puede compartir errores con la redacción y no sustituye una verificación humana.', 'Los artículos automatizados indican esa autoría. No afirmamos haber probado herramientas o realizado experimentos cuando no lo hemos hecho. No fabricamos experiencias, testimonios ni usuarios.'] },
      { heading: 'Qué publicamos y qué corregimos', text: ['Preferimos no publicar una noticia que no supere los controles. No prometemos un artículo cada día. Diferenciamos los datos de las fuentes de nuestras recomendaciones y señalamos las limitaciones conocidas.', 'Las fuentes originales se enlazan en cada artículo. Si detectas un error, escribe a admin@foroiaaldia.com indicando la URL. Podemos corregir o retirar contenido; las fechas del artículo reflejan sus actualizaciones.'] }
    ]
  },
  normas: {
    title: 'Normas de la comunidad', description: 'Normas para participar y moderación de comentarios en Foro IA al Día.',
    blocks: [
      { heading: 'Participación responsable', text: ['Debate las ideas con respeto. No publiques acoso, suplantaciones, spam, datos personales de otras personas ni material que no tengas derecho a compartir. Aporta contexto a enlaces y recomendaciones; declara relaciones comerciales relevantes.'] },
      { heading: 'Comentarios moderados', text: ['Para comentar necesitas una cuenta verificada y un artículo con comentarios habilitados. Los comentarios nuevos pasan por moderación. Al editar uno vuelve a revisión y deja de ser público hasta su aprobación. Puedes retirar tus propios comentarios desde tu cuenta.', 'El registro puede permanecer cerrado durante el lanzamiento. El foro se ofrece actualmente para lectura: no hay creación de temas o respuestas desde las cuentas de miembros.'] },
      { heading: 'Incidencias', text: ['Podemos rechazar o retirar comentarios y bloquear cuentas por incumplimientos, con registro interno de las decisiones. Para comunicar un problema o pedir revisión escribe a admin@foroiaaldia.com. No publiques tu denuncia con datos privados en los comentarios.'] }
    ]
  },
  'aviso-legal': {
    title: 'Aviso legal', description: 'Identificación y condiciones de uso de Foro IA al Día.',
    blocks: [
      { heading: 'La publicación', text: ['Foro IA al Día es una publicación sobre inteligencia artificial en español accesible en foroiaaldia.com. El correo de contacto es admin@foroiaaldia.com. La identificación del titular se muestra en esta página una vez confirmada por la persona responsable.'] },
      { heading: 'Uso de los contenidos', text: ['Los artículos son informativos. Las referencias a productos y organizaciones no implican afiliación o respaldo. Las marcas y materiales de terceros pertenecen a sus titulares; las fuentes enlazadas mantienen sus propias condiciones.', 'No prometemos resultados económicos, posicionamiento ni exactitud absoluta. Comprueba las fuentes y las condiciones actuales de una herramienta antes de tomar decisiones. Si detectas un posible uso indebido de contenido, comunícalo por el correo de contacto.'] }
    ]
  },
  privacidad: {
    title: 'Privacidad', description: 'Datos tratados por Foro IA al Día, finalidades y vías de contacto.',
    blocks: [
      { heading: 'Qué datos utiliza la web', text: ['Puedes leer los artículos sin registrarte. Para servir y proteger las conexiones se procesan datos técnicos, incluida la dirección IP. Los límites de acceso utilizan identificadores derivados mediante hash; esto no convierte automáticamente toda la información técnica en anónima.', 'Las cuentas, cuando se habilitan, usan correo, nombre público y contraseña protegida mediante hash. Guardamos sesiones, comentarios y decisiones de moderación para prestar esas funciones y protegerlas. No mostramos públicamente el correo de las cuentas.'] },
      { heading: 'Finalidades y conservación', text: ['La gestión de una cuenta y sus comentarios permite prestar las funciones solicitadas. Las medidas de seguridad y moderación protegen el servicio frente a abusos. Los mensajes que envíes al correo se utilizan para atender tu solicitud, no para suscribirte a publicidad.', 'Las sesiones caducan a los siete días. Los enlaces de recuperación caducan a los treinta minutos y los de verificación a las veinticuatro horas. La caducidad impide utilizarlos; no equivale por sí sola a borrar inmediatamente todos los registros. Los expedientes de investigación automática tienen una retención de treinta días y su historial económico se conserva para controlar el presupuesto.'] },
      { heading: 'Proveedores y automatización', text: ['La aplicación y la base de datos se alojan en un VPS de OVHcloud en Polonia. El correo de contacto está configurado mediante una redirección de OVHcloud a un buzón de Google. Los comentarios y credenciales de las cuentas no se envían al modelo de redacción.', 'Cuando se activa la investigación, OpenAI recibe documentos públicos seleccionados e instrucciones para redactar y revisar. La IA no decide la moderación de cuentas ni tiene acceso directo a la base de datos. No se cargan anuncios. La disponibilidad de analítica opcional se indica al final de esta página.'] },
      { heading: 'Tus solicitudes', text: ['Puedes solicitar acceso, rectificación, supresión y, cuando corresponda, oposición, limitación y portabilidad escribiendo a admin@foroiaaldia.com. No adjuntes documentos de identidad por defecto. También puedes consultar a la Agencia Española de Protección de Datos y presentar una reclamación ante ella.'] }
    ]
  },
  cookies: {
    title: 'Cookies', description: 'Cookies de sesión y seguridad utilizadas por Foro IA al Día.',
    blocks: [
      { heading: 'Sesión y protección de formularios', text: ['Al iniciar sesión, foroia_session mantiene el acceso a la cuenta y foroia_csrf protege las acciones contra solicitudes de otros sitios. Ambas pertenecen a este dominio y tienen una duración máxima de siete días. La cookie de sesión es HttpOnly; en producción ambas se envían mediante HTTPS.', 'Cerrar sesión elimina estas cookies. Puedes borrarlas desde tu navegador; tendrás que volver a identificarte y las acciones de cuenta pueden dejar de funcionar hasta hacerlo.'] },
      { heading: 'Contadores propios', text: ['Guardamos únicamente día, ruta pública y un contador agregado de cargas HTML para seguir la evolución del blog. No usamos cookies de analítica ni guardamos IP, referente o identificadores de visitantes en estos contadores. Se conservan los agregados para comparar la evolución histórica.'] },
      { heading: 'Servicios externos', text: ['Esta versión no incorpora cookies publicitarias, vídeos incrustados ni fuentes externas. El estado de la analítica opcional se indica más abajo. Los enlaces a las fuentes abren páginas de terceros con sus propias políticas. Si se añaden anuncios o analítica, se actualizará esta información y se preparará el consentimiento que corresponda antes de cargarlos.'] }
    ]
  }
}
