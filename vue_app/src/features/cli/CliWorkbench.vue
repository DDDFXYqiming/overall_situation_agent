<template>
  <main class="workbench">
    <section class="hero-panel">
      <div>
        <span class="label">CLI 代理</span>
        <h2>把命令行智能体能力映射成可点击工作流</h2>
        <p>导入、生成报告、导入并生成、上下文和报告命令都复用同一套后端能力。</p>
      </div>
      <BaseButton variant="primary" @click="chatStore.send('/help')"><TerminalSquare :size="16" />查看 CLI 帮助</BaseButton>
    </section>

    <section class="command-grid">
      <article v-for="command in commands" :key="command.title" class="command-card">
        <div class="command-card__head">
          <component :is="command.icon" :size="18" />
          <strong>{{ command.title }}</strong>
        </div>
        <code>{{ command.preview }}</code>
        <p>{{ command.description }}</p>
        <BaseButton :variant="command.primary ? 'primary' : 'secondary'" @click="command.run">
          {{ command.action }}
        </BaseButton>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { DatabaseZap, FileText, Play, TerminalSquare } from "lucide-vue-next";
import BaseButton from "@/components/ui/BaseButton.vue";
import { useChatStore } from "@/stores/chatStore";
import { useImportStore } from "@/stores/importStore";

const chatStore = useChatStore();
const importStore = useImportStore();

const inputArg = computed(() => importStore.inputPath || "<主数据 Excel 或目录>");
const scheduleArg = computed(() => importStore.scheduleInput || "<赛事日 Excel>");

const commands = computed(() => [
  {
    title: "import",
    description: "把 Excel 文件或目录导入 Elasticsearch。",
    preview: `python -m overall_situation_agent.cli import --input "${inputArg.value}"${importStore.recreateIndex ? " --recreate-index" : ""}`,
    action: "执行导入",
    icon: DatabaseZap,
    primary: false,
    run: () => chatStore.submitJobCommand("import")
  },
  {
    title: "report",
    description: "基于当前索引生成 HTML 和 Markdown 报告。",
    preview: `python -m overall_situation_agent.cli report --schedule-input "${scheduleArg.value}"`,
    action: "生成报告",
    icon: FileText,
    primary: false,
    run: () => chatStore.submitJobCommand("report")
  },
  {
    title: "run",
    description: "先导入数据，再生成整体情况报告。",
    preview: `python -m overall_situation_agent.cli run --input "${inputArg.value}" --schedule-input "${scheduleArg.value}"`,
    action: "导入并生成",
    icon: Play,
    primary: true,
    run: () => chatStore.submitJobCommand("run")
  },
  {
    title: "chat",
    description: "进入持续问答智能体，支持 /help、/context、/report。",
    preview: `python -m overall_situation_agent.cli chat --schedule-input "${scheduleArg.value}"`,
    action: "回到对话",
    icon: TerminalSquare,
    primary: false,
    run: () => chatStore.send("你能做什么")
  }
]);
</script>

<style scoped>
.workbench {
  min-height: 0;
  overflow: auto;
  padding: 28px clamp(18px, 4vw, 48px);
}

.hero-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: white;
  padding: 22px;
  box-shadow: var(--shadow-sm);
}

.label {
  color: var(--accent);
  font: 700 12px/1 var(--font-mono);
  text-transform: uppercase;
}

h2 {
  margin: 8px 0;
  font-size: 22px;
}

p {
  margin: 0;
  color: var(--muted-foreground);
  line-height: 1.6;
}

.command-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.command-card {
  display: grid;
  gap: 12px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: white;
  padding: 18px;
}

.command-card__head {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--accent);
}

code {
  overflow: auto;
  border-radius: 9px;
  background: #0f172a;
  color: white;
  padding: 12px;
  font: 500 12px/1.6 var(--font-mono);
}

@media (max-width: 760px) {
  .hero-panel,
  .command-grid {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
