

AUTOCUTSEL_PACKAGE="autocutsel" # Используется для организации буфера обмена для VNC сессии, см. https://superuser.com/a/1524282
if is_termux; then
    AUTOCUTSEL_PACKAGE=""
elif is_msys; then
    AUTOCUTSEL_PACKAGE=""
fi