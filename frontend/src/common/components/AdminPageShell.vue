<script lang="ts" setup>
import type { StateCard } from "@@/apis/admin/type"

defineProps<{
  title: string
  description: string
  cards: StateCard[]
}>()
</script>

<template>
  <div class="admin-page">
    <section class="hero">
      <div class="hero-copy">
        <span class="hero-badge">MTLogin Console</span>
        <h1>{{ title }}</h1>
        <p>{{ description }}</p>
        <div class="hero-actions">
          <slot name="actions" />
        </div>
      </div>
      <div class="hero-cards">
        <article v-for="card in cards" :key="card.label" class="state-card">
          <span class="state-card__label">{{ card.label }}</span>
          <strong class="state-card__value">{{ card.value || "--" }}</strong>
        </article>
      </div>
    </section>
    <section class="page-body">
      <slot />
    </section>
  </div>
</template>

<style lang="scss" scoped>
.admin-page {
  min-height: 100%;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgb(14 165 233 / 14%), transparent 22%),
    radial-gradient(circle at top right, rgb(16 185 129 / 16%), transparent 18%),
    linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr);
  gap: 18px;
  margin-bottom: 20px;
}

.hero-copy,
.state-card,
.page-body :deep(.panel-card) {
  border: 1px solid rgb(148 163 184 / 14%);
  border-radius: 24px;
  background: rgb(255 255 255 / 84%);
  box-shadow: 0 18px 46px rgb(15 23 42 / 8%);
  backdrop-filter: blur(18px);
}

.hero-copy {
  padding: 28px;
}

.hero-badge {
  display: inline-flex;
  margin-bottom: 14px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgb(15 118 110 / 10%);
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: #0f172a;
  font-size: clamp(28px, 4vw, 38px);
  line-height: 1.1;
}

p {
  margin: 14px 0 0;
  max-width: 56ch;
  color: #475569;
  font-size: 15px;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 22px;
}

.hero-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.state-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 22px;
}

.state-card__label {
  color: #64748b;
  font-size: 13px;
}

.state-card__value {
  color: #0f172a;
  font-size: 18px;
  line-height: 1.5;
}

.page-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-body :deep(.el-input),
.page-body :deep(.el-select),
.page-body :deep(.el-date-editor),
.page-body :deep(.el-input-number),
.page-body :deep(.el-textarea) {
  width: 100%;
}

.page-body :deep(.el-form-item__label) {
  color: #334155;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.page-body :deep(.el-input__wrapper),
.page-body :deep(.el-textarea__inner),
.page-body :deep(.el-select__wrapper),
.page-body :deep(.el-date-editor.el-input__wrapper),
.page-body :deep(.el-input-number) {
  border-radius: 16px;
  background: linear-gradient(180deg, rgb(248 250 252 / 96%), rgb(255 255 255 / 98%));
  box-shadow:
    0 0 0 1px rgb(148 163 184 / 18%),
    inset 0 1px 0 rgb(255 255 255 / 85%);
  transition:
    box-shadow 0.2s ease,
    background-color 0.2s ease,
    transform 0.2s ease;
}

.page-body :deep(.el-input__wrapper),
.page-body :deep(.el-select__wrapper),
.page-body :deep(.el-date-editor.el-input__wrapper) {
  min-height: 44px;
  padding-inline: 14px;
}

.page-body :deep(.el-input-number .el-input__wrapper) {
  min-height: 44px;
  padding-inline: 44px 14px;
}

.page-body :deep(.el-input__wrapper.is-focus),
.page-body :deep(.el-select__wrapper.is-focused),
.page-body :deep(.el-date-editor.el-input__wrapper.is-focus),
.page-body :deep(.el-textarea__inner:focus),
.page-body :deep(.el-input-number:hover) {
  box-shadow:
    0 0 0 1px rgb(14 165 233 / 48%),
    0 10px 24px rgb(14 165 233 / 12%),
    inset 0 1px 0 rgb(255 255 255 / 90%);
}

.page-body :deep(.el-input__inner),
.page-body :deep(.el-textarea__inner),
.page-body :deep(.el-select__placeholder),
.page-body :deep(.el-input-number .el-input__inner) {
  color: #0f172a;
  font-size: 14px;
}

.page-body :deep(.el-input__prefix-inner),
.page-body :deep(.el-input__suffix-inner) {
  color: #64748b;
}

@media (max-width: 1080px) {
  .hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .admin-page {
    padding: 18px;
  }

  .hero-cards {
    grid-template-columns: 1fr;
  }
}
</style>
