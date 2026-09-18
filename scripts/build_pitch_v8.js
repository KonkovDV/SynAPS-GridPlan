/**
 * Honest Energotechhub pitch. Numbers from benchmark/results/deck_facts.json.
 * Public entry: python scripts/build_deck.py
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

// CI-gated claim_ids from docs/CLAIMS_REGISTRY.md: V1 V2 V3 B1 B2 B3 B4 B5 B7 P6 P8 M6
// Package version 0.1.8 is injected from versions.py via deck_facts.json; footer uses git describe.

const BG = "0B1117";
const CARD = "151D26";
const INK = "E8EEF4";
const MUTED = "8B9AAB";
const AMBER = "E8A54B";
const OK = "3D9B7A";
const STOP = "C45C4A";
const LINE = "2A3542";

let FACTS;

function loadFacts() {
  const factsPath = path.join(__dirname, "..", "benchmark", "results", "deck_facts.json");
  if (!fs.existsSync(factsPath)) {
    process.stderr.write("missing deck_facts.json; run python scripts/deck_facts.py\n");
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(factsPath, "utf8"));
}

function footer(slide, n, total) {
  slide.addText(`SynAPS-GridPlan ${FACTS.git_describe}  ·  лабораторный прототип  ·  не пилот`, {
    x: 0.5,
    y: 7.12,
    w: 10.5,
    h: 0.22,
    fontFace: "Calibri",
    fontSize: 11,
    color: MUTED,
    margin: 0,
  });
  slide.addText(`${n} / ${total}`, {
    x: 11.6,
    y: 7.12,
    w: 1.2,
    h: 0.22,
    fontFace: "Calibri",
    fontSize: 11,
    color: MUTED,
    align: "right",
    margin: 0,
  });
}

function kicker(slide, text) {
  slide.addText(text, {
    x: 0.5,
    y: 0.28,
    w: 12.3,
    h: 0.28,
    fontFace: "Calibri",
    fontSize: 12,
    color: AMBER,
    bold: true,
    charSpacing: 1.2,
    margin: 0,
  });
}

async function main() {
  FACTS = loadFacts();
  const jury = FACTS.jury;
  const budgetParts = String(FACTS.budget).split(" = ")[0].split("/");
  const pres = new pptxgen();
  pres.defineLayout({ name: "WIDE", width: 13.3, height: 7.5 });
  pres.layout = "WIDE";
  pres.title = `SynAPS-GridPlan ${FACTS.gridplan_version} — evidence pitch`;
  pres.author = FACTS.author;
  pres.company = FACTS.company;
  pres.subject = "Энерготехнохаб Петербург, направление 02";

  const total = 12;

  // 1 title
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0,
      y: 0,
      w: 0.18,
      h: 7.5,
      fill: { color: AMBER },
    });
    s.addText("ЭНЕРГОТЕХНОХАБ ПЕТЕРБУРГ  ·  НАПРАВЛЕНИЕ 02  ·  ПРИЁМ ДО 25.09.2026  ·  P6", {
      x: 0.55,
      y: 0.45,
      w: 12.2,
      h: 0.3,
      fontFace: "Calibri",
      fontSize: 13,
      color: AMBER,
      margin: 0,
    });
    s.addText("SynAPS-GridPlan", {
      x: 0.55,
      y: 1.15,
      w: 12.2,
      h: 0.7,
      fontFace: "Calibri",
      fontSize: 40,
      bold: true,
      color: INK,
      margin: 0,
    });
    s.addText(
      "Воспроизводимое ядро планирования работ ТОиР:\nгенерация отдельно, проверка отдельно.",
      {
        x: 0.55,
        y: 1.95,
        w: 11.5,
        h: 1.15,
        fontFace: "Calibri",
        fontSize: 22,
        color: INK,
        margin: 0,
      }
    );
    const chips = [
      ["версия", `${FACTS.gridplan_version} V1`],
      ["зрелость", FACTS.trl_sentence + "  V3"],
      ["данные", "synthetic only"],
      ["лицензия", "MIT, закрытого ядра нет"],
    ];
    chips.forEach((c, i) => {
      const x = 0.55 + (i % 4) * 3.1;
      s.addShape(pres.shapes.RECTANGLE, {
        x,
        y: 3.4,
        w: 2.95,
        h: 1.15,
        fill: { color: CARD },
      });
      s.addText(c[0], {
        x: x + 0.15,
        y: 3.5,
        w: 2.65,
        h: 0.3,
        fontFace: "Calibri",
        fontSize: 12,
        color: MUTED,
        margin: 0,
      });
      s.addText(c[1], {
        x: x + 0.15,
        y: 3.82,
        w: 2.65,
        h: 0.55,
        fontFace: "Calibri",
        fontSize: 14,
        bold: true,
        color: INK,
        margin: 0,
      });
    });
    s.addText(
      "Не партнёр Россети. Не планировщик смен. Не аттестация ГОСТ Р 58048 и 187-ФЗ.\nСледующий этап — shadow-пилот с владельцем процесса, не акт внедрения в декабре.",
      {
        x: 0.55,
        y: 4.8,
        w: 12.2,
        h: 0.85,
        fontFace: "Calibri",
        fontSize: 15,
        color: MUTED,
        margin: 0,
      }
    );
    s.addText("github.com/KonkovDV/SynAPS-GridPlan  ·  docs/CLAIMS_REGISTRY.md", {
      x: 0.55,
      y: 6.55,
      w: 12.2,
      h: 0.3,
      fontFace: "Calibri",
      fontSize: 13,
      color: MUTED,
      margin: 0,
    });
    footer(s, 1, total);
  }

  // 2 thesis
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "ТЕЗИС");
    s.addText("Что просим оценить — и чего не обещаем", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 26,
      bold: true,
      color: INK,
      margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5,
      y: 1.2,
      w: 12.3,
      h: 1.55,
      fill: { color: CARD },
    });
    s.addText(
      "С индустриальным заказчиком за один следующий этап формализуем реальные ограничения площадки и проведём измеримый shadow-пилот. ИИ, если появится, только переводит текст в JSON; жёсткие правила меняет человек, график публикует человек.",
      {
        x: 0.7,
        y: 1.35,
        w: 11.9,
        h: 1.25,
        fontFace: "Calibri",
        fontSize: 16,
        color: INK,
        margin: 0,
      }
    );
    const cols = [
      [
        "Есть в git",
        "JSON-постановка → GREED/FIFO/CP-SAT → независимый checker. Fail-closed. Синтетический макет " +
          jury.jobs +
          " работ.",
      ],
      [
        "Нужна валидация",
        "Один процесс ТОиР заказчика: владелец, данные, цена ошибки, baseline. Не переносить макет «РЭС» на нефтегаз без интервью.",
      ],
      [
        "Не отправлять",
        "v7 Dark: опрос 312, SCHEDBench vs GREED, ГОСТ §5 смен, 4.2 ч CP-SAT, партнёры, живой пилот в декабре.",
      ],
    ];
    cols.forEach((c, i) => {
      const x = 0.5 + i * 4.15;
      s.addShape(pres.shapes.RECTANGLE, {
        x,
        y: 3.0,
        w: 3.95,
        h: 3.7,
        fill: { color: CARD },
      });
      s.addText(c[0], {
        x: x + 0.2,
        y: 3.2,
        w: 3.55,
        h: 0.45,
        fontFace: "Calibri",
        fontSize: 16,
        bold: true,
        color: i === 2 ? STOP : AMBER,
        margin: 0,
      });
      s.addText(c[1], {
        x: x + 0.2,
        y: 3.75,
        w: 3.55,
        h: 2.7,
        fontFace: "Calibri",
        fontSize: 15,
        color: INK,
        margin: 0,
      });
    });
    footer(s, 2, total);
  }

  // 3 architecture
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "КАК УСТРОЕНО");
    s.addText("Генерация не имеет права подтвердить сама себя", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 26,
      bold: true,
      color: INK,
      margin: 0,
    });
    const steps = [
      ["1", "Вход JSON/CSV", "live", "Схема Pydantic. Не SCADA."],
      ["2", "Поиск слотов", "prototype", "GREED / FIFO — эвристики. CP-SAT — makespan скомпилированной модели."],
      ["3", "Checker", "live", "Жёсткое нарушение ⇒ план не verified_feasible, CLI exit 2."],
      ["4", "Человек", "planned", "Публикация графика, наряд, переключение — вне продукта."],
    ];
    steps.forEach((st, i) => {
      const y = 1.25 + i * 1.2;
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.5,
        y,
        w: 12.3,
        h: 1.08,
        fill: { color: CARD },
      });
      s.addText(st[0], {
        x: 0.7,
        y: y + 0.28,
        w: 0.5,
        h: 0.5,
        fontFace: "Calibri",
        fontSize: 22,
        bold: true,
        color: AMBER,
        margin: 0,
      });
      s.addText(st[1], {
        x: 1.35,
        y: y + 0.14,
        w: 4.2,
        h: 0.4,
        fontFace: "Calibri",
        fontSize: 18,
        bold: true,
        color: INK,
        margin: 0,
      });
      s.addText(st[2], {
        x: 5.6,
        y: y + 0.18,
        w: 1.6,
        h: 0.32,
        fontFace: "Calibri",
        fontSize: 12,
        color: AMBER,
        margin: 0,
      });
      s.addText(st[3], {
        x: 7.3,
        y: y + 0.18,
        w: 5.2,
        h: 0.72,
        fontFace: "Calibri",
        fontSize: 14,
        color: MUTED,
        margin: 0,
      });
    });
    footer(s, 3, total);
  }

  // 4 evidence
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "ЛАБОРАТОРИЯ  ·  ОДИН ИНСТАНС  ·  B1 B2 B3 B4 B5 B7");
    s.addText("Синтетический макет " + jury.jobs + " работ — не выгрузка Россети", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });
    s.addTable(
      [
        [
          { text: "Solver", options: { fill: { color: LINE }, color: INK, bold: true } },
          { text: "Hard violations", options: { fill: { color: LINE }, color: INK, bold: true } },
          { text: "Checker", options: { fill: { color: LINE }, color: INK, bold: true } },
          { text: "Статус", options: { fill: { color: LINE }, color: INK, bold: true } },
        ],
        ["FIFO (календарный)", String(jury.fifo_hard), jury.fifo_checker, "недопустим"],
        ["GREED", String(jury.greed_hard), jury.greed_checker, "heuristic_feasible"],
        ["CPSAT-30, тот же JSON", String(jury.cpsat_hard), jury.cpsat_verified, jury.cpsat_status + " makespan"],
      ],
      {
        x: 0.5,
        y: 1.2,
        w: 12.3,
        h: 2.6,
        colW: [3.6, 2.7, 2.5, 3.5],
        border: [{ pt: 0 }, { pt: 0 }, { pt: 0 }, { pt: 0 }],
        fontFace: "Calibri",
        fontSize: 14,
        color: INK,
        align: "left",
        valign: "middle",
        fill: { color: CARD },
      }
    );
    s.addText(
      "Источник: benchmark/results/jury_report.md и test_res_cpsat_proves_optimal_makespan. Воспроизведение: python scripts/evidence_bundle.py. Время стены — машина, не SLA. Аварийные сутки (23 работы) и фидер 200/600 — другие датасеты, не складывать. GREED не оптимален потому, что checker зелёный.",
      {
        x: 0.5,
        y: 4.05,
        w: 12.3,
        h: 1.35,
        fontFace: "Calibri",
        fontSize: 15,
        color: MUTED,
        margin: 0,
      }
    );
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5,
      y: 5.5,
      w: 12.3,
      h: 1.35,
      fill: { color: CARD },
    });
    s.addText(
      "Полнота GREED не доказана: неуспех эвристики ≠ невыполнимость. Адаптер берёт одно окно, не объединение альтернатив. CP-SAT 4.2 часа из v7 в репозитории нет.",
      {
        x: 0.7,
        y: 5.65,
        w: 11.9,
        h: 1.05,
        fontFace: "Calibri",
        fontSize: 15,
        color: INK,
        margin: 0,
      }
    );
    footer(s, 4, total);
  }

  // 5 not claims
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "ГРАНИЦЫ");
    s.addText("Снято из v7, чтобы не сжечь отбор", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 26,
      bold: true,
      color: INK,
      margin: 0,
    });
    const kills = [
      ["ГОСТ Р 58048 §5 смены", "Стандарт — методика УГТ, не чередование смен и не штрафы КИИ."],
      ["187-ФЗ «с 2024»", "Закон от 26.07.2017. On-prem ≠ аттестация КИИ."],
      ["84.8% / n=312 / 2300 РЭС", "Первички в git нет. Не повторять."],
      ["GREED 100% vs GPT 55.9%", "SCHEDBench — 1132 текстовых задач. У нас 55 структурированных работ."],
      ["REST, облако, 1С, поды", "В git — CLI. Остальное planned."],
      ["Партнёры / акт в декабре", "Декабрь — Демо-день программы. Партнёрства нет."],
    ];
    kills.forEach((k, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.5 + col * 6.4;
      const y = 1.2 + row * 1.75;
      s.addShape(pres.shapes.RECTANGLE, {
        x,
        y,
        w: 6.15,
        h: 1.6,
        fill: { color: CARD },
      });
      s.addText(k[0], {
        x: x + 0.2,
        y: y + 0.15,
        w: 5.75,
        h: 0.4,
        fontFace: "Calibri",
        fontSize: 16,
        bold: true,
        color: STOP,
        margin: 0,
      });
      s.addText(k[1], {
        x: x + 0.2,
        y: y + 0.6,
        w: 5.75,
        h: 0.8,
        fontFace: "Calibri",
        fontSize: 14,
        color: INK,
        margin: 0,
      });
    });
    footer(s, 5, total);
  }

  // 6 scenario
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "ПРОМЫШЛЕННЫЙ СЦЕНАРИЙ  ·  ГИПОТЕЗА");
    s.addText("Окна ТОиР и ресурсов — не ростер смен", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 26,
      bold: true,
      color: INK,
      margin: 0,
    });
    s.addText(
      "Планировщик одного подразделения: работы, квалификации бригад, технологические цепочки, заморозка согласованных слотов, допустимый простой. Сценарий требует интервью с владельцем процесса. Специфику сетевого макета нельзя без проверки переносить на нефтегазовую площадку.",
      {
        x: 0.5,
        y: 1.15,
        w: 12.3,
        h: 1.2,
        fontFace: "Calibri",
        fontSize: 16,
        color: INK,
        margin: 0,
      }
    );
    const boxes = [
      ["Вход", "Обезличенные работы, бригады, окна, ЗИП-позиции, freeze. approved=true — не ЭП диспетчера."],
      ["Выход", "Кандидат + протокол нарушений. Не наряд, не команда оборудованию."],
      ["Вне скоупа", "N-1, SAIDI, SCADA, 1С:ТОИР как замена, электрический режим."],
    ];
    boxes.forEach((b, i) => {
      const x = 0.5 + i * 4.15;
      s.addShape(pres.shapes.RECTANGLE, {
        x,
        y: 2.55,
        w: 3.95,
        h: 2.55,
        fill: { color: CARD },
      });
      s.addText(b[0], {
        x: x + 0.2,
        y: 2.7,
        w: 3.55,
        h: 0.4,
        fontFace: "Calibri",
        fontSize: 16,
        bold: true,
        color: AMBER,
        margin: 0,
      });
      s.addText(b[1], {
        x: x + 0.2,
        y: 3.2,
        w: 3.55,
        h: 1.7,
        fontFace: "Calibri",
        fontSize: 14,
        color: INK,
        margin: 0,
      });
    });
    s.addText("Запрос к заказчику программы: не «подписать пилот», а дать владельца процесса и согласованный срез.", {
      x: 0.5,
      y: 5.3,
      w: 12.3,
      h: 1.4,
      fontFace: "Calibri",
      fontSize: 16,
      color: MUTED,
      margin: 0,
    });
    footer(s, 6, total);
  }

  // 7 UGT
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "ГОСТ Р 58048-2017  ·  САМООЦЕНКА");
    s.addText("УГТ4 лабораторный макет есть; УГТ5 — нет", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 26,
      bold: true,
      color: INK,
      margin: 0,
    });
    s.addTable(
      [
        [
          { text: "Индикатор", options: { fill: { color: LINE }, color: INK, bold: true } },
          { text: "Сейчас", options: { fill: { color: LINE }, color: INK, bold: true } },
        ],
        ["Базовая функция в упрощённой среде", "Да: синтетика, CI, checker"],
        ["Требования заказчика", "Нет"],
        ["Фактические промышленные данные", "Нет"],
        ["Испытание в окружении, близком к реальному (УГТ5)", "Нет → shadow-пилот"],
        ["ISO 16290 TRL 4 в коде", "Самооценка космической шкалы, не сертификат ГОСТ"],
      ],
      {
        x: 0.5,
        y: 1.2,
        w: 12.3,
        h: 4.2,
        colW: [7.2, 5.1],
        border: [{ pt: 0 }, { pt: 0 }, { pt: 0 }, { pt: 0 }],
        fontFace: "Calibri",
        fontSize: 14,
        color: INK,
        fill: { color: CARD },
        valign: "middle",
      }
    );
    s.addText("Маршрут 4→5 = подписанный контракт данных + тень без управления оборудованием.", {
      x: 0.5,
      y: 5.55,
      w: 12.3,
      h: 1.2,
      fontFace: "Calibri",
      fontSize: 16,
      color: MUTED,
      margin: 0,
    });
    footer(s, 7, total);
  }

  // 8 pilot
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "СЛЕДУЮЩИЙ ЭТАП");
    s.addText("Shadow-пилот: готовы запустить, когда есть владелец", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });
    const ph = [
      ["1. Контракт данных", "Словарь полей, hard/soft, владелец правила."],
      ["2. Baseline", "Исторический график и ручной/простой метод на том же горизонте."],
      ["3. Адаптация", "CSV/JSON, freeze, трассировка правила → checker → тест."],
      ["4. Тень", "Кандидат не идёт в наряд. Разбор с диспетчером, ИТ, ИБ."],
      ["5. GO/NO-GO", "Только совместно. Нет данных → остаёмся на TRL 4."],
    ];
    ph.forEach((p, i) => {
      const y = 1.15 + i * 0.95;
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.5,
        y,
        w: 12.3,
        h: 0.85,
        fill: { color: CARD },
      });
      s.addText(p[0], {
        x: 0.7,
        y: y + 0.22,
        w: 3.6,
        h: 0.42,
        fontFace: "Calibri",
        fontSize: 16,
        bold: true,
        color: AMBER,
        margin: 0,
      });
      s.addText(p[1], {
        x: 4.4,
        y: y + 0.18,
        w: 8.1,
        h: 0.52,
        fontFace: "Calibri",
        fontSize: 15,
        color: INK,
        margin: 0,
      });
    });
    footer(s, 8, total);
  }

  // 9 money
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "ПРИЗ ПРОГРАММЫ  ·  ПРЕДМЕТ СОГЛАСОВАНИЯ  ·  P8 M6");
    s.addText("1,5 млн ₽ — если присудят, не «два инженера по 750»", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });
    s.addTable(
      [
        [
          { text: "Статья", options: { fill: { color: LINE }, color: INK, bold: true } },
          { text: "тыс. ₽", options: { fill: { color: LINE }, color: INK, bold: true } },
        ],
        ["Доменная формализация и данные", budgetParts[0]],
        ["Solver / checker / тесты", budgetParts[1]],
        ["Интеграция и on-prem упаковка", budgetParts[2]],
        ["ИБ, журнал, документация", budgetParts[3]],
        ["Проведение тени и оценка", budgetParts[4]],
        ["IP / юрработы / резерв", budgetParts[5]],
      ],
      {
        x: 0.5,
        y: 1.2,
        w: 8.4,
        h: 4.4,
        colW: [6.2, 2.2],
        border: [{ pt: 0 }, { pt: 0 }, { pt: 0 }, { pt: 0 }],
        fontFace: "Calibri",
        fontSize: 14,
        color: INK,
        fill: { color: CARD },
        valign: "middle",
      }
    );
    s.addShape(pres.shapes.RECTANGLE, {
      x: 9.15,
      y: 1.2,
      w: 3.65,
      h: 4.4,
      fill: { color: CARD },
    });
    s.addText("Статус", {
      x: 9.35,
      y: 1.4,
      w: 3.25,
      h: 0.35,
      fontFace: "Calibri",
      fontSize: 14,
      color: MUTED,
      margin: 0,
    });
    s.addText("assumption", {
      x: 9.35,
      y: 1.8,
      w: 3.25,
      h: 0.4,
      fontFace: "Calibri",
      fontSize: 18,
      bold: true,
      color: AMBER,
      margin: 0,
    });
    s.addText(
      "Анонс СПбПУ: претендовать на 1 500 000 ₽. Не оферта заказчику. Не SaaS 90 тыс. из v7.",
      {
        x: 9.35,
        y: 2.4,
        w: 3.25,
        h: 2.8,
        fontFace: "Calibri",
        fontSize: 14,
        color: INK,
        margin: 0,
      }
    );
    footer(s, 9, total);
  }

  // 10 team
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "РЕСУРСЫ");
    s.addText("Один автор репозиториев. Дыры названы.", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 26,
      bold: true,
      color: INK,
      margin: 0,
    });
    const roles = [
      ["Есть", "Коньков Д.В. — публичный git SynAPS и GridPlan, MIT."],
      ["Нет в git", "Предметный эксперт ТОиР, интегратор 1С/EAM, ИБ-аттестат."],
      ["Программа", "Техноброкеры хаба — менторы отбора, не партнёры продукта."],
      ["IP", "Весь опубликованный контур MIT. Open-core как второй контур не существует."],
    ];
    roles.forEach((r, i) => {
      const y = 1.25 + i * 1.2;
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.5,
        y,
        w: 12.3,
        h: 1.05,
        fill: { color: CARD },
      });
      s.addText(r[0], {
        x: 0.75,
        y: y + 0.3,
        w: 2.4,
        h: 0.45,
        fontFace: "Calibri",
        fontSize: 16,
        bold: true,
        color: AMBER,
        margin: 0,
      });
      s.addText(r[1], {
        x: 3.3,
        y: y + 0.25,
        w: 9.2,
        h: 0.55,
        fontFace: "Calibri",
        fontSize: 16,
        color: INK,
        margin: 0,
      });
    });
    footer(s, 10, total);
  }

  // 11 ask
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "ЗАПРОС");
    s.addText("Не акт в декабре. Интервью и тень.", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 26,
      bold: true,
      color: INK,
      margin: 0,
    });
    const asks = [
      ["Сейчас", "Отбор в программу. Работа с техноброкером и заказчиком ТЭК."],
      ["После отбора", "Владелец процесса, обезличенный срез, критерии GO/NO-GO."],
      ["Демо-день (14–20.12, СПб)", "Показать протокол тени или честный NO-GO. Не живой контур."],
      ["Не просим", "Называть хаб или Россети партнёрами. Принять лабораторные " + jury.fifo_hard + " как эффект сети."],
    ];
    asks.forEach((a, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.5 + col * 6.4;
      const y = 1.25 + row * 2.5;
      s.addShape(pres.shapes.RECTANGLE, {
        x,
        y,
        w: 6.15,
        h: 2.3,
        fill: { color: CARD },
      });
      s.addText(a[0], {
        x: x + 0.25,
        y: y + 0.25,
        w: 5.65,
        h: 0.45,
        fontFace: "Calibri",
        fontSize: 16,
        bold: true,
        color: a[0] === "Не просим" ? STOP : AMBER,
        margin: 0,
      });
      s.addText(a[1], {
        x: x + 0.25,
        y: y + 0.85,
        w: 5.65,
        h: 1.15,
        fontFace: "Calibri",
        fontSize: 16,
        color: INK,
        margin: 0,
      });
    });
    footer(s, 11, total);
  }

  // 12 reproduce
  {
    const s = pres.addSlide();
    s.background = { color: BG };
    kicker(s, "ПРОВЕРИТЬ РУКАМИ");
    s.addText("Один commit, одна команда, без картинки из дека", {
      x: 0.5,
      y: 0.58,
      w: 12.3,
      h: 0.45,
      fontFace: "Calibri",
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5,
      y: 1.2,
      w: 12.3,
      h: 2.35,
      fill: { color: CARD },
    });
    s.addText(
      "python -m pip install -e \".[dev]\" --force-reinstall\npython -m synaps_gridplan version\npython scripts/evidence_bundle.py",
      {
        x: 0.75,
        y: 1.4,
        w: 11.8,
        h: 1.95,
        fontFace: "Consolas",
        fontSize: 16,
        color: AMBER,
        margin: 0,
      }
    );
    s.addText(
      "Должно напечатать " +
        FACTS.gridplan_version +
        " и пин SynAPS " +
        FACTS.synaps_commit12 +
        "… [V1] [V2]. Jury + CP-SAT на том же res_severny. Реестр: docs/CLAIMS_REGISTRY.md. Почему не v7: docs/PITCH_V7_FACTCHECK.md. Программа: https://www.etechhubspb.ru/accelerator",
      {
        x: 0.5,
        y: 3.75,
        w: 12.3,
        h: 1.2,
        fontFace: "Calibri",
        fontSize: 16,
        color: INK,
        margin: 0,
      }
    );
    s.addText("Подача до 25 сентября. Не в последнюю минуту. Не этим v7.", {
      x: 0.5,
      y: 5.15,
      w: 12.3,
      h: 1.5,
      fontFace: "Calibri",
      fontSize: 20,
      bold: true,
      color: INK,
      margin: 0,
    });
    footer(s, 12, total);
  }

  const out = path.join(__dirname, "..", "SynAPS_v8_Evidence.pptx");
  await pres.writeFile({ fileName: out });
  process.stdout.write(out + "\n");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
