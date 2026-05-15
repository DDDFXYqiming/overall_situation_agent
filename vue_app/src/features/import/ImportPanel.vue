<template>
  <aside class="import-panel">
    <header>
      <div>
        <h2>配置与导入</h2>
        <p>{{ configStore.apiUrl }}</p>
      </div>
      <ChevronsRight :size="20" />
    </header>

    <section class="panel-section">
      <h3>数据导入</h3>
      <FieldRow label="数据文件路径">
        <div class="path-input">
          <input v-model="importStore.inputPath" placeholder="Excel 文件或目录绝对路径" />
          <label title="上传主数据">
            <FolderUp :size="17" />
            <input type="file" accept=".xlsx,.xlsm" multiple @change="uploadInput" />
          </label>
        </div>
      </FieldRow>

      <FieldRow label="调度输入路径">
        <div class="path-input">
          <input v-model="importStore.scheduleInput" placeholder="赛事日 Excel 文件路径" />
          <label title="上传赛程">
            <CalendarDays :size="17" />
            <input type="file" accept=".xlsx,.xlsm" @change="uploadSchedule" />
          </label>
        </div>
      </FieldRow>

      <label class="toggle-row">
        <span>
          <strong>重建索引</strong>
          <small>开启后将删除并重建 ES 索引</small>
        </span>
        <input v-model="importStore.recreateIndex" type="checkbox" />
      </label>
      <p v-if="importStore.uploadMessage" class="hint">{{ importStore.uploadMessage }}</p>
      <p v-if="importStore.error" class="error">{{ importStore.error }}</p>
    </section>

    <section class="panel-section">
      <h3>时间范围</h3>
      <div class="date-grid">
        <FieldRow label="开始日期"><input v-model="importStore.startDate" type="date" /></FieldRow>
        <FieldRow label="结束日期"><input v-model="importStore.endDate" type="date" /></FieldRow>
      </div>
      <FieldRow label="输出路径">
        <input v-model="importStore.output" placeholder="可选：report.html" />
      </FieldRow>
    </section>

    <section class="panel-section">
      <h3>服务配置</h3>
      <div class="service-grid">
        <FieldRow label="API Host"><input :value="configStore.apiUrl" readonly /></FieldRow>
        <FieldRow label="索引"><input :value="configStore.esIndex" readonly /></FieldRow>
      </div>
      <div class="action-grid">
        <BaseButton variant="secondary" :disabled="!importStore.canImport || jobsStore.isBusy" @click="submitImport">
          <DatabaseZap :size="16" />导入数据
        </BaseButton>
        <BaseButton variant="secondary" :disabled="jobsStore.isBusy" @click="submitReport">
          <FileText :size="16" />生成报告
        </BaseButton>
        <BaseButton variant="primary" :disabled="!importStore.canImport || jobsStore.isBusy" @click="submitRun">
          <Play :size="16" />导入并生成
        </BaseButton>
      </div>
    </section>

    <JobProgress />
  </aside>
</template>

<script setup lang="ts">
import { CalendarDays, ChevronsRight, DatabaseZap, FileText, FolderUp, Play } from "lucide-vue-next";
import BaseButton from "@/components/ui/BaseButton.vue";
import FieldRow from "@/components/ui/FieldRow.vue";
import JobProgress from "@/features/jobs/JobProgress.vue";
import { useConfigStore } from "@/stores/configStore";
import { useImportStore } from "@/stores/importStore";
import { useJobsStore } from "@/stores/jobsStore";

const configStore = useConfigStore();
const importStore = useImportStore();
const jobsStore = useJobsStore();

function filesFromEvent(event: Event) {
  const input = event.target as HTMLInputElement;
  return Array.from(input.files || []);
}

async function uploadInput(event: Event) {
  await importStore.uploadInputFiles(filesFromEvent(event));
}

async function uploadSchedule(event: Event) {
  await importStore.uploadScheduleFile(filesFromEvent(event));
}

function submitImport() {
  void jobsStore.submit("import", importStore.importPayload());
}

function submitReport() {
  void jobsStore.submit("report", importStore.reportPayload());
}

function submitRun() {
  void jobsStore.submit("run", importStore.runPayload());
}
</script>

<style scoped>
.import-panel {
  min-height: 100vh;
  display: grid;
  align-content: start;
  gap: 0;
  background: #fff;
}

header {
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
}

h2,
h3,
p {
  margin: 0;
}

h2 {
  font-size: 17px;
}

header p {
  margin-top: 5px;
  color: var(--muted-foreground);
  font: 500 12px/1 var(--font-mono);
}

.panel-section {
  display: grid;
  gap: 14px;
  padding: 18px 18px 20px;
  border-bottom: 1px solid var(--border);
}

h3 {
  font-size: 15px;
}

input {
  width: 100%;
  height: 38px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: white;
  color: var(--foreground);
  padding: 0 11px;
  font: 500 13px/1 var(--font-ui);
}

input:focus {
  border-color: rgba(0, 82, 255, 0.55);
  outline: 2px solid rgba(0, 82, 255, 0.14);
}

.path-input {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 40px;
  gap: 8px;
}

.path-input label {
  height: 38px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: 9px;
  color: var(--muted-foreground);
  cursor: pointer;
}

.path-input label:hover {
  color: var(--accent);
  border-color: rgba(0, 82, 255, 0.3);
}

.path-input input[type="file"] {
  display: none;
}

.toggle-row {
  min-height: 46px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toggle-row span {
  display: grid;
  gap: 4px;
}

.toggle-row strong {
  font-size: 13px;
}

.toggle-row small {
  color: var(--muted-foreground);
  font-size: 12px;
}

.toggle-row input {
  width: 42px;
  height: 24px;
  appearance: none;
  border: 0;
  border-radius: 999px;
  background: #cbd5e1;
  padding: 2px;
  transition: background 160ms ease;
}

.toggle-row input::before {
  content: "";
  display: block;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: white;
  box-shadow: var(--shadow-sm);
  transition: transform 160ms ease;
}

.toggle-row input:checked {
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
}

.toggle-row input:checked::before {
  transform: translateX(18px);
}

.date-grid,
.service-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.action-grid .base-button:last-child {
  grid-column: 1 / -1;
}

.hint,
.error {
  border-radius: 8px;
  padding: 9px 10px;
  font-size: 12px;
}

.hint {
  background: rgba(0, 82, 255, 0.07);
  color: var(--accent);
}

.error {
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
}

@media (max-width: 1180px) {
  .import-panel {
    grid-column: 2;
    min-height: auto;
    border-top: 1px solid var(--border);
  }
}

@media (max-width: 820px) {
  .import-panel {
    grid-column: auto;
  }
}
</style>
