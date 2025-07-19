const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Цвета для консоли
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

// Вспомогательные функции
const log = {
  info: (msg) => console.log(`${colors.blue}ℹ${colors.reset} ${msg}`),
  success: (msg) => console.log(`${colors.green}✓${colors.reset} ${msg}`),
  error: (msg) => console.log(`${colors.red}✗${colors.reset} ${msg}`),
  warn: (msg) => console.log(`${colors.yellow}⚠${colors.reset} ${msg}`),
  header: (msg) => console.log(`\n${colors.cyan}${colors.bright}=== ${msg} ===${colors.reset}\n`)
};

// Определяем пути
const paths = {
  genDir: path.join(__dirname, 'static', 'gen'),
  srcDir: path.join(__dirname, 'src'),
  staticDir: path.join(__dirname, 'static'),
  config: path.join(__dirname, 'obfuscator.config.json')
};

// Проверка наличия исходных файлов
function findSourceFiles() {
  const possiblePaths = [
    { misc: path.join(paths.srcDir, 'misc.js'), tasks: path.join(paths.srcDir, 'tasks.js'), location: 'src' },
    { misc: path.join(paths.staticDir, 'misc.js'), tasks: path.join(paths.staticDir, 'tasks.js'), location: 'static' }
  ];

  for (const pathSet of possiblePaths) {
    if (fs.existsSync(pathSet.misc) && fs.existsSync(pathSet.tasks)) {
      return pathSet;
    }
  }

  return null;
}

// Основная функция сборки
function buildAssets() {
  log.header('Сборка обфусцированных JS файлов');

  // 1. Создаем папку gen если её нет
  if (!fs.existsSync(paths.genDir)) {
    fs.mkdirSync(paths.genDir, { recursive: true });
    log.success(`Создана папка ${path.relative(__dirname, paths.genDir)}`);
  }

  // 2. Очищаем старые файлы
  log.info('Очистка старых файлов...');
  const oldFiles = fs.readdirSync(paths.genDir).filter(file => file.endsWith('.obf.js'));
  
  if (oldFiles.length > 0) {
    oldFiles.forEach(file => {
      fs.unlinkSync(path.join(paths.genDir, file));
      log.warn(`Удален: ${file}`);
    });
  } else {
    log.info('Старых файлов не найдено');
  }

  // 3. Находим исходные файлы
  const sourcePaths = findSourceFiles();
  if (!sourcePaths) {
    log.error('Исходные JS файлы не найдены!');
    log.info('Ожидаемые пути:');
    log.info('  - src/misc.js и src/tasks.js');
    log.info('  - static/misc.js и static/tasks.js');
    process.exit(1);
  }

  log.success(`Исходные файлы найдены в папке: ${sourcePaths.location}/`);

  // 4. Проверяем наличие конфигурации
  const hasConfig = fs.existsSync(paths.config);
  if (!hasConfig) {
    log.warn('Файл obfuscator.config.json не найден, используются параметры по умолчанию');
  }

  // 5. Обфусцируем файлы
  const files = [
    { name: 'misc.js', input: sourcePaths.misc, output: path.join(paths.genDir, 'misc.obf.js') },
    { name: 'tasks.js', input: sourcePaths.tasks, output: path.join(paths.genDir, 'tasks.obf.js') }
  ];

  log.header('Обфускация файлов');

  let successCount = 0;
  files.forEach(file => {
    try {
      log.info(`Обработка ${file.name}...`);
      
      // Получаем размер исходного файла
      const originalSize = fs.statSync(file.input).size;
      
      // Формируем команду
      let cmd = `npx javascript-obfuscator "${file.input}" --output "${file.output}"`;
      
      if (hasConfig) {
        cmd += ` --config "${paths.config}"`;
      } else {
        // Базовые параметры обфускации
        cmd += ' --compact true';
        cmd += ' --control-flow-flattening true';
        cmd += ' --dead-code-injection true';
        cmd += ' --string-array true';
        cmd += ' --string-array-encoding base64';
        cmd += ' --string-array-threshold 0.75';
        cmd += ' --split-strings true';
        cmd += ' --transform-object-keys true';
      }
      
      // Выполняем обфускацию
      execSync(cmd, { stdio: 'pipe' });
      
      // Проверяем результат
      if (fs.existsSync(file.output)) {
        const obfuscatedSize = fs.statSync(file.output).size;
        const increase = ((obfuscatedSize / originalSize - 1) * 100).toFixed(1);
        
        log.success(`Создан: ${path.basename(file.output)}`);
        console.log(`${colors.dim}  Исходный: ${(originalSize / 1024).toFixed(2)} KB`);
        console.log(`  Обфусцированный: ${(obfuscatedSize / 1024).toFixed(2)} KB`);
        console.log(`  Увеличение: ${increase}%${colors.reset}`);
        
        // Проверяем, что файл действительно обфусцирован
        const content = fs.readFileSync(file.output, 'utf8').substring(0, 200);
        if (content.includes('_0x') || content.includes('const _')) {
          console.log(`${colors.dim}  ✓ Файл успешно обфусцирован${colors.reset}`);
        } else {
          log.warn('Файл может быть не полностью обфусцирован');
        }
        
        successCount++;
      } else {
        log.error(`Не удалось создать ${file.output}`);
      }
      
    } catch (error) {
      log.error(`Ошибка при обфускации ${file.name}: ${error.message}`);
    }
  });

  // 6. Итоги
  log.header('Результаты сборки');
  
  if (successCount === files.length) {
    log.success(`Все файлы обфусцированы успешно (${successCount}/${files.length})`);
    
    console.log(`\n${colors.bright}Итоговые файлы:${colors.reset}`);
    const finalFiles = fs.readdirSync(paths.genDir).filter(file => file.endsWith('.js'));
    finalFiles.forEach(file => {
      const stats = fs.statSync(path.join(paths.genDir, file));
      console.log(`  ${colors.green}•${colors.reset} ${file} (${(stats.size / 1024).toFixed(2)} KB)`);
    });
    
    console.log(`\n${colors.green}${colors.bright}✨ Сборка завершена успешно!${colors.reset}`);
    console.log(`${colors.dim}Обфусцированные файлы: ${path.relative(__dirname, paths.genDir)}/${colors.reset}`);
  } else {
    log.error(`Обфусцировано только ${successCount} из ${files.length} файлов`);
    process.exit(1);
  }
}

// Запуск сборки
try {
  buildAssets();
} catch (error) {
  console.error(`\n${colors.red}${colors.bright}Критическая ошибка:${colors.reset} ${error.message}`);
  process.exit(1);
}