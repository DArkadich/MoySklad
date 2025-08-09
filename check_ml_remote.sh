#!/bin/bash

# Конфигурация - ИЗМЕНИТЕ НА ВАШ АДРЕС СЕРВЕРА
PROD_SERVER="${1:-denis@localhost}"
PROD_PATH="~/MoySklad"

echo "🔍 УДАЛЕННАЯ ПРОВЕРКА ML-МОДЕЛЕЙ НА ПРОДАКШНЕ"
echo "================================================"
echo "📅 Время проверки: $(date)"
echo "🌐 Сервер: $PROD_SERVER"
echo "📁 Путь: $PROD_PATH"
echo ""

# Проверка параметров
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "📖 ИСПОЛЬЗОВАНИЕ:"
    echo "   $0 [сервер]"
    echo ""
    echo "📋 ПРИМЕРЫ:"
    echo "   $0 denis@192.168.1.100"
    echo "   $0 denis@prod-server.local"
    echo "   $0 denis@localhost"
    echo ""
    echo "🔧 НАСТРОЙКА SSH:"
    echo "   1. Добавьте в ~/.ssh/config:"
    echo "      Host prod-server"
    echo "          HostName 192.168.1.100"
    echo "          User denis"
    echo "          IdentityFile ~/.ssh/id_ed25519"
    echo "   2. Затем используйте: $0 denis@prod-server"
    echo ""
    exit 0
fi

# Проверка SSH соединения
echo "1️⃣ ПРОВЕРКА SSH СОЕДИНЕНИЯ"
echo "---------------------------"

if ssh -o ConnectTimeout=10 -o BatchMode=yes "$PROD_SERVER" "echo 'SSH соединение установлено'" 2>/dev/null; then
    echo "✅ SSH соединение установлено"
else
    echo "❌ Не удалось установить SSH соединение"
    echo ""
    echo "🔧 РЕШЕНИЕ:"
    echo "   1. Укажите правильный адрес сервера:"
    echo "      $0 denis@IP_АДРЕС_СЕРВЕРА"
    echo ""
    echo "   2. Или добавьте в ~/.ssh/config:"
    echo "      Host prod-server"
    echo "          HostName IP_АДРЕС_СЕРВЕРА"
    echo "          User denis"
    echo "          IdentityFile ~/.ssh/id_ed25519"
    echo ""
    echo "   3. Проверьте доступность сервера:"
    echo "      ping IP_АДРЕС_СЕРВЕРА"
    echo ""
    echo "📖 Справка: $0 --help"
    exit 1
fi

# Запуск проверки ML моделей на продакшн-сервере
echo ""
echo "2️⃣ ЗАПУСК ПРОВЕРКИ ML МОДЕЛЕЙ"
echo "-------------------------------"

echo "🚀 Выполняем проверку на продакшн-сервере..."
ssh "$PROD_SERVER" "cd $PROD_PATH && ./check_production_ml.sh"

# Проверка статуса выполнения
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Проверка завершена успешно"
else
    echo ""
    echo "⚠️ Проверка завершена с предупреждениями"
fi

echo ""
echo "📅 Удаленная проверка завершена: $(date)"
echo ""
echo "💡 ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ:"
echo "   • Подключиться к серверу: ssh $PROD_SERVER"
echo "   • Проверить логи: ssh $PROD_SERVER 'cd $PROD_PATH && docker-compose logs'"
echo "   • Перезапустить систему: ssh $PROD_SERVER 'cd $PROD_PATH && ./restart_system_fixed.sh'"
