import os
import shutil
import subprocess
import sys
from datetime import datetime


def clean_gen_folder():
    gen_path = 'static/gen'
    
    if os.path.exists(gen_path):
        print(f"Очистка папки {gen_path}...")
        files = os.listdir(gen_path)
        if files:
            print("Удаляемые файлы:")
            for file in files:
                if file.endswith('.js'):
                    print(f"  - {file}")
        
        for file in files:
            if file.endswith('.js'):
                os.remove(os.path.join(gen_path, file))
    else:
        os.makedirs(gen_path, exist_ok=True)
    
    print("✓ Папка готова\n")


def check_source_files():
    possible_locations = [
        ('src/misc.js', 'src/tasks.js'),
        ('static/misc.js', 'static/tasks.js')
    ]
    
    for misc_path, tasks_path in possible_locations:
        if os.path.exists(misc_path) and os.path.exists(tasks_path):
            return misc_path, tasks_path
    
    return None, None


def check_nodejs():
    node_cmd = None
    npm_cmd = None
    
    for cmd in ['node', 'nodejs']:
        try:
            node_version = subprocess.check_output([cmd, '--version'], 
                                                 text=True, stderr=subprocess.DEVNULL).strip()
            node_cmd = cmd
            break
        except:
            continue
    
    for cmd in ['npm', 'npm.cmd']:
        try:
            npm_version = subprocess.check_output([cmd, '--version'], 
                                                text=True, stderr=subprocess.DEVNULL).strip()
            npm_cmd = cmd
            break
        except:
            continue
    
    if node_cmd and npm_cmd:
        print(f"✓ Node.js: {node_version}")
        print(f"✓ NPM: {npm_version}\n")
        return True
    
    return False


def build_without_obfuscation():
    print("=== Сборка без обфускации ===\n")
    
    misc_path, tasks_path = check_source_files()
    if not misc_path:
        print("✗ Исходные JS файлы не найдены!")
        print("Создание базовых JS файлов...")
        create_basic_js_files()
        misc_path, tasks_path = check_source_files()
        if not misc_path:
            return False
    
    gen_path = 'static/gen'
    os.makedirs(gen_path, exist_ok=True)
    
    try:
        shutil.copy2(misc_path, os.path.join(gen_path, 'misc.obf.js'))
        shutil.copy2(tasks_path, os.path.join(gen_path, 'tasks.obf.js'))
        
        print("✓ Файлы скопированы (без обфускации)")
        verify_results()
        return True
        
    except Exception as e:
        print(f"✗ Ошибка копирования: {e}")
        return False


def create_basic_js_files():
    os.makedirs('static', exist_ok=True)
    
    misc_js = '''console.log('Misc.js loaded');

function showMessage(message) {
    if (message) {
        alert(message);
    }
}

function toggleElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = element.style.display === 'none' ? 'block' : 'none';
    }
}'''
    
    tasks_js = '''console.log('Tasks.js loaded');

function submitTask(taskId) {
    console.log('Submitting task:', taskId);
    const form = document.getElementById('task-form-' + taskId);
    if (form) {
        form.submit();
    }
}

function validateTaskForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const inputs = form.querySelectorAll('input[required], textarea[required]');
    for (let input of inputs) {
        if (!input.value.trim()) {
            alert('Заполните все обязательные поля');
            input.focus();
            return false;
        }
    }
    return true;
}'''
    
    try:
        with open('static/misc.js', 'w', encoding='utf-8') as f:
            f.write(misc_js)
        
        with open('static/tasks.js', 'w', encoding='utf-8') as f:
            f.write(tasks_js)
        
        print("✓ Созданы базовые JS файлы")
        
    except Exception as e:
        print(f"✗ Ошибка создания файлов: {e}")
        return False
    
    return True















def cleanup_source_files():
    """Удаляет исходные JS файлы после успешной обфускации"""
    source_files = [
        'static/misc.js',
        'static/tasks.js',
        'src/misc.js', 
        'src/tasks.js'
    ]
    
    print("\nУдаление исходных файлов...")
    for filepath in source_files:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"  ✓ Удален {filepath}")
            except Exception as e:
                print(f"  ⚠️  Не удалось удалить {filepath}: {e}")

def build_assets():
    print("=== Сборка ресурсов для production ===")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    clean_gen_folder()
    
    if not check_nodejs():
        print("✗ Node.js или NPM не найдены!")
        print("  Возможные решения:")
        print("  1. Установите Node.js с https://nodejs.org/")
        print("  2. Перезапустите терминал после установки")
        print("  3. Проверьте PATH")
        return False
    
    misc_path, tasks_path = check_source_files()
    if not misc_path:
        print("✗ Исходные JS файлы не найдены!")
        print("Создание базовых JS файлов...")
        if not create_basic_js_files():
            return False
        misc_path, tasks_path = check_source_files()
        if not misc_path:
            return False
    
    print(f"✓ Найдены исходные файлы:")
    print(f"  - {misc_path}")
    print(f"  - {tasks_path}\n")
    
    if not os.path.exists('package.json'):
        print("Создание package.json...")
        create_default_package_json()
    
    if not os.path.exists('node_modules') or not os.path.exists('node_modules/javascript-obfuscator'):
        print("Установка зависимостей...")
        result = subprocess.run(['npm', 'install'], shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"✗ Ошибка установки: {result.stderr}")
            return False
        print("✓ Зависимости установлены\n")
    
    if not os.path.exists('obfuscator.config.json'):
        print("Создание конфигурации обфускатора...")
        create_obfuscator_config()
    
    success = False
    
    if os.path.exists('build_assets_js.js'):
        print("Запуск обфускации через build_assets_js.js...")
        result = subprocess.run(['node', 'build_assets_js.js'], shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Обфускация завершена успешно\n")
            verify_results()
            success = True
        else:
            print(f"✗ Ошибка: {result.stderr}")
            print("Пробуем альтернативный метод...\n")
    
    if not success:
        success = run_direct_obfuscation(misc_path, tasks_path)
    
    if success:
        cleanup_source_files()  # Удаляем исходные файлы после успешной обфускации
    
    return success

def run_direct_obfuscation(misc_path, tasks_path):
    print("Запуск прямой обфускации...")
    
    files = [
        (misc_path, 'static/gen/misc.obf.js'),
        (tasks_path, 'static/gen/tasks.obf.js')
    ]
    
    for input_file, output_file in files:
        print(f"\nОбфускация {os.path.basename(input_file)}...")
        
        cmd = ['npx', 'javascript-obfuscator', input_file, '--output', output_file]
        
        if os.path.exists('obfuscator.config.json'):
            cmd.extend(['--config', 'obfuscator.config.json'])
        else:
            cmd.extend([
                '--compact', 'true',
                '--control-flow-flattening', 'true',
                '--dead-code-injection', 'true',
                '--string-array', 'true',
                '--string-array-encoding', 'base64'
            ])
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"✗ Ошибка: {result.stderr}")
            return False
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✓ Создан {output_file} ({size:,} байт)")
        else:
            print(f"✗ Файл {output_file} не создан")
            return False
    
    verify_results()
    return True













def verify_results():
    gen_path = 'static/gen'
    print("\nПроверка результатов:")
    
    expected_files = ['misc.obf.js', 'tasks.obf.js']
    
    for filename in expected_files:
        filepath = os.path.join(gen_path, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"  ✓ {filename} ({size:,} байт)")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(500)
                if any(marker in content for marker in ['_0x', 'const _', 'var _']):
                    print(f"    → Файл обфусцирован")
                else:
                    print(f"    → Файл скопирован без обфускации")
        else:
            print(f"  ✗ {filename} НЕ НАЙДЕН")


def create_default_package_json():
    package_json = {
        "name": "ds_py",
        "version": "1.0.0",
        "description": "Dark School Security Learning Platform",
        "scripts": {
            "build": "node build_assets_js.js",
            "build:direct": "npm run obfuscate:misc && npm run obfuscate:tasks",
            "obfuscate:misc": "javascript-obfuscator src/misc.js --output static/gen/misc.obf.js --config obfuscator.config.json",
            "obfuscate:tasks": "javascript-obfuscator src/tasks.js --output static/gen/tasks.obf.js --config obfuscator.config.json",
            "obfuscate:misc:static": "javascript-obfuscator static/misc.js --output static/gen/misc.obf.js --config obfuscator.config.json",
            "obfuscate:tasks:static": "javascript-obfuscator static/tasks.js --output static/gen/tasks.obf.js --config obfuscator.config.json",
            "clean": "rimraf static/gen/*.js"
        },
        "devDependencies": {
            "javascript-obfuscator": "^4.1.0",
            "rimraf": "^5.0.5"
        },
        "author": "",
        "license": "ISC"
    }
    
    import json
    with open('package.json', 'w', encoding='utf-8') as f:
        json.dump(package_json, f, indent=2)
    print("✓ Создан package.json")


def create_obfuscator_config():
    config = {
        "compact": True,
        "controlFlowFlattening": True,
        "controlFlowFlatteningThreshold": 0.75,
        "deadCodeInjection": True,
        "deadCodeInjectionThreshold": 0.4,
        "debugProtection": False,
        "debugProtectionInterval": 0,
        "disableConsoleOutput": True,
        "identifierNamesGenerator": "hexadecimal",
        "log": False,
        "numbersToExpressions": True,
        "renameGlobals": False,
        "rotateStringArray": True,
        "selfDefending": True,
        "simplify": True,
        "splitStrings": True,
        "splitStringsChunkLength": 10,
        "stringArray": True,
        "stringArrayCallsTransform": True,
        "stringArrayCallsTransformThreshold": 0.5,
        "stringArrayEncoding": ["base64"],
        "stringArrayIndexShift": True,
        "stringArrayRotate": True,
        "stringArrayShuffle": True,
        "stringArrayWrappersCount": 2,
        "stringArrayWrappersChainedCalls": True,
        "stringArrayWrappersParametersMaxCount": 4,
        "stringArrayWrappersType": "function",
        "stringArrayThreshold": 0.75,
        "transformObjectKeys": True,
        "unicodeEscapeSequence": False
    }
    
    import json
    with open('obfuscator.config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print("✓ Создан obfuscator.config.json")


if __name__ == "__main__":
    print("\n🚀 Dark School - Сборка производственных ресурсов\n")
    
    if build_assets():
        print("\n✅ Сборка завершена успешно!")
        print("   Обфусцированные файлы находятся в static/gen/")
        print("   Теперь можете запустить приложение с USE_OBFUSCATED=True")
    else:
        print("\n⚠️  Пробуем сборку без обфускации...")
        if build_without_obfuscation():
            print("\n✅ Сборка завершена (без обфускации)!")
            print("   Файлы находятся в static/gen/")
            print("   Приложение будет работать с USE_OBFUSCATED=True")
            cleanup_source_files()
        else:
            print("\n❌ Сборка завершена с ошибками!")
            print("   Проверьте сообщения об ошибках выше")