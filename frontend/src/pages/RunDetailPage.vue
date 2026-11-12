<template>
  <section>
    <nav data-testid="run-detail-breadcrumb" class="uno-mb-3 uno-flex uno-items-center uno-gap-2 uno-text-sm uno-text-[#607174]">
      <button
        type="button"
        class="uno-inline-flex uno-cursor-pointer uno-items-center uno-gap-1 uno-border-0 uno-bg-transparent uno-p-0 uno-text-[#304345] hover:uno-text-[#132a2d]"
        @click="goBack"
      >
        <i class="pi pi-angle-left uno-text-xs" />
        <span>{{ t('common.back') }}</span>
      </button>
      <span class="uno-text-[#9ab0b1]">/</span>
      <span>{{ t('runs.runDetail') }}</span>
    </nav>

    <PageHeader
      :eyebrow="t('runs.eyebrow')"
      :title="selectedRun ? runHeaderTitle : t('runs.runDetail')"
      :description="t('runs.description')"
    >
      <template #actions>
        <div v-if="selectedRun" data-testid="run-detail-history-badge" class="uno-relative">
          <OverlayBadge :value="historyRunCount" severity="contrast">
            <Button
              data-testid="run-detail-history-toggle"
              icon="pi pi-calendar"
              severity="secondary"
              :aria-label="t('runs.historyCalendar')"
              @click="historyPickerOpen = !historyPickerOpen"
            />
          </OverlayBadge>
          <div
            v-if="historyPickerOpen"
            data-testid="run-detail-history-panel"
            class="uno-absolute uno-right-0 uno-top-[calc(100%+0.45rem)] uno-z-20 uno-grid uno-gap-3 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3 uno-shadow-lg"
          >
            <span class="uno-text-sm uno-text-[#607174]">{{ t('runs.historySelectDate') }}</span>
            <DatePicker
              :model-value="historyPickerValue"
              inline
              date-format="yy-mm-dd"
              :manual-input="false"
              :disabled-dates="historyDisabledDates"
              :min-date="historyMinDate"
              :max-date="historyMaxDate"
              @update:model-value="handleHistoryDateSelect"
            />
          </div>
        </div>
        <Button
          v-if="canCancelRun"
          icon="pi pi-stop"
          :label="t('runs.stopAnalysis')"
          severity="danger"
          outlined
          :disabled="!canWrite"
          @click="cancelRun"
        />
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="() => loadRunDetail()" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <details v-if="selectedRun" data-testid="run-detail-pinned-action-card" class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-4 uno-py-[0.85rem]">
      <summary class="uno-cursor-pointer uno-font-700">{{ t('runs.pinnedAction') }}</summary>
      <div class="uno-mt-3 uno-grid uno-grid-cols-[repeat(auto-fit,minmax(180px,1fr))] uno-gap-[0.8rem]">
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinCategory') }}</span>
          <Select v-model="pinForm.category" :options="categoryOptions" option-label="label" option-value="value" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinPriority') }}</span>
          <Select v-model="pinForm.priority" :options="priorityOptions" option-label="label" option-value="value" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinStatus') }}</span>
          <Select v-model="pinForm.action_status" :options="actionStatusOptions" option-label="label" option-value="value" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinAssignee') }}</span>
          <Select v-model="pinForm.assignee" :options="memberOptions" option-label="label" option-value="value" :placeholder="t('common.optional')" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinNextAction') }}</span>
          <InputText v-model="pinForm.next_action" :placeholder="t('runs.pinNextAction')" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinDueDate') }}</span>
          <InputText v-model="pinForm.due_date" type="date" :disabled="!canWrite" />
        </label>
      </div>
      <Textarea v-model="pinForm.note" rows="3" auto-resize :placeholder="t('runs.pinNote')" class="uno-mt-3 uno-w-full" :disabled="!canWrite" />
      <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-justify-end uno-gap-[0.55rem]">
        <Button icon="pi pi-bookmark" :label="t('runs.savePinnedAction')" severity="secondary" :disabled="!canWrite" @click="savePinnedRun" />
        <Button v-if="currentPinnedRun" icon="pi pi-times" :label="t('runs.removePinnedAction')" severity="danger" outlined :disabled="!canWrite" @click="deletePinnedRun" />
      </div>
    </details>

    <Card v-if="selectedRun" data-testid="run-detail-main-card">
      <template #title>{{ t('runs.runDetail') }}</template>
      <template #content>
        <div class="uno-grid uno-gap-4">
          <div class="uno-grid uno-gap-[0.9rem] uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-[#fbfdfd] uno-p-4">
            <div class="uno-flex uno-items-start uno-justify-between uno-gap-4">
              <div>
                <p class="uno-m-0 uno-text-xs uno-font-700 uno-uppercase uno-text-[#6f8183]">{{ t('runs.summary') }}</p>
                <h2 class="uno-mb-0 uno-mt-[0.15rem] uno-text-[1.2rem] uno-tracking-normal uno-text-[#132a2d]">{{ runIdentityLabel }} · {{ selectedRun.date }}</h2>
              </div>
              <Tag :value="selectedRun.signal || selectedRun.status" :severity="signalSeverity(selectedRun.signal || selectedRun.status)" />
            </div>
            <MetricGrid :items="detailMetrics" />
            <div class="uno-grid uno-grid-cols-4 max-[1100px]:uno-grid-cols-2 max-[640px]:uno-grid-cols-1 uno-gap-[0.65rem]">
              <div v-for="item in decisionItems" :key="item.label" class="uno-grid uno-min-w-0 uno-gap-1 uno-rounded-lg uno-border uno-border-[#dbe6e6] uno-bg-white uno-p-3">
                <span class="uno-text-[0.78rem] uno-text-[#607174]">{{ item.label }}</span>
                <strong class="uno-min-w-0 uno-break-words uno-text-[#132a2d]">{{ item.value }}</strong>
              </div>
            </div>
            <p class="uno-m-0 uno-leading-[1.55] uno-text-[#304345]">{{ decisionSummary }}</p>
          </div>

          <div data-testid="run-detail-insight-panels" class="uno-grid uno-gap-3">
            <div v-for="panel in insightPanels" :key="panel.key" class="uno-min-w-0 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-[0.85rem]">
              <span class="uno-text-[#6f8183]">{{ insightTitle(panel.key) }}</span>
              <ul v-if="panel.items.length" class="uno-mb-0 uno-mt-[0.55rem] uno-grid uno-gap-[0.45rem] uno-pl-[1.1rem] uno-leading-[1.45] uno-text-[#304345]">
                <li v-for="item in panel.items" :key="item">{{ item }}</li>
              </ul>
              <p v-else class="uno-text-[#6f8183]">{{ t('runs.noInsight') }}</p>
            </div>
          </div>

          <Card v-if="dataFetches.length" data-testid="run-detail-data-sources-card">
            <template #title>{{ t('runs.dataSources') }}</template>
            <template #content>
              <div v-if="dataWarnings.length" data-testid="run-detail-data-warnings" class="uno-mb-4 uno-rounded-lg uno-border uno-border-[#f1d38a] uno-bg-[#fff8e6] uno-p-3">
                <p class="uno-m-0 uno-font-700 uno-text-[#7b5b12]">{{ t('runs.dataWarnings') }}</p>
                <ul class="uno-mb-0 uno-mt-2 uno-grid uno-gap-1 uno-pl-[1.1rem] uno-text-[#7b5b12]">
                  <li v-for="warning in dataWarnings" :key="String(warning.key || warning.message || '')">{{ warning.message }}</li>
                </ul>
              </div>

              <div class="uno-grid uno-gap-3">
                <div
                  v-for="entry in dataFetches"
                  :key="String(entry.key || '')"
                  class="uno-grid uno-gap-2 uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3"
                >
                  <div class="uno-flex uno-flex-wrap uno-items-start uno-justify-between uno-gap-3">
                    <div class="uno-grid uno-gap-1">
                      <strong class="uno-text-[#132a2d]">{{ dataFetchItemLabel(entry) }}</strong>
                      <small class="uno-text-[#6f8183]">{{ String(entry.request_label || '') }}</small>
                    </div>
                    <Tag :value="dataFetchStatusLabel(entry)" :severity="dataFetchStatusSeverity(entry)" />
                  </div>
                  <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-2">
                    <div class="uno-grid uno-gap-1">
                      <span class="uno-text-[0.78rem] uno-text-[#6f8183]">{{ t('runs.actualSource') }}</span>
                      <strong class="uno-text-[#132a2d]">{{ dataFetchSourceLabel(entry.actual_source, entry.status) }}</strong>
                    </div>
                    <div class="uno-grid uno-gap-1">
                      <span class="uno-text-[0.78rem] uno-text-[#6f8183]">{{ t('runs.configuredSources') }}</span>
                      <span class="uno-text-[#304345]">{{ dataFetchSourceList(entry.configured_sources) }}</span>
                    </div>
                    <div class="uno-grid uno-gap-1">
                      <span class="uno-text-[0.78rem] uno-text-[#6f8183]">{{ t('runs.attemptedSources') }}</span>
                      <span class="uno-text-[#304345]">{{ dataFetchSourceList(entry.attempted_sources) }}</span>
                    </div>
                  </div>
                  <p v-if="String(entry.detail || '').trim()" class="uno-m-0 uno-text-[#304345]">{{ entry.detail }}</p>
                  <div v-if="String(entry.result_preview || '').trim()" class="uno-grid uno-gap-1">
                    <span class="uno-text-[0.78rem] uno-text-[#6f8183]">{{ t('runs.resultPreview') }}</span>
                    <pre class="uno-m-0 uno-max-h-[180px] uno-overflow-auto uno-whitespace-pre-wrap uno-break-words uno-rounded-lg uno-bg-[#f8fbfb] uno-p-3 uno-text-[#304345]">{{ String(entry.result_preview || '') }}</pre>
                  </div>
                </div>
              </div>
            </template>
          </Card>

          <div
            data-testid="run-detail-section-tabs"
            class="uno-sticky uno-top-[76px] uno-z-[6] uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white/95 uno-p-1.5 uno-shadow-sm uno-backdrop-blur-md max-[900px]:uno-top-[128px]"
          >
            <div class="uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
              <div class="uno-flex uno-flex-wrap uno-gap-1" role="tablist" :aria-label="t('runs.reportSections')">
                <button
                  v-for="section in sectionOptions"
                  :key="section.value"
                  type="button"
                  role="tab"
                  :aria-selected="selectedSectionKey === section.value"
                  :class="[
                    'uno-min-h-10 uno-cursor-pointer uno-rounded-lg uno-border-b-2 uno-border-transparent uno-px-3 uno-py-[0.55rem] uno-text-sm uno-font-600',
                    selectedSectionKey === section.value
                      ? 'uno-bg-[#162326] uno-text-white uno-shadow-sm'
                      : 'uno-bg-transparent uno-text-[#304345] hover:uno-bg-[#f4f8f8] hover:uno-text-[#132a2d]',
                  ]"
                  @click="selectedSectionKey = section.value"
                >
                  {{ section.label }}
                </button>
              </div>
              <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                <Button icon="pi pi-refresh" :label="t('common.retry')" severity="secondary" :disabled="!canWrite" @click="retryRun" />
                <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined :disabled="!canWrite" @click="deleteRun" />
              </div>
            </div>
          </div>

          <ReportMarkdown
            data-testid="run-detail-report-markdown"
            :content="selectedSectionText"
            :empty-text="t('runs.noReport')"
            :constrain-height="false"
          />

          <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(280px,1fr))] uno-gap-4">
            <Card data-testid="run-detail-comments-card">
              <template #title>{{ t('runs.comments') }}</template>
              <template #content>
                <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                  <Select v-model="commentAuthor" :options="memberOptions" option-label="label" option-value="value" :placeholder="t('runs.commentAuthor')" :disabled="!canWrite" />
                </div>
                <Textarea v-model="commentBody" rows="3" auto-resize :placeholder="t('runs.commentPlaceholder')" class="uno-mt-3 uno-w-full" :disabled="!canWrite" />
                <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                  <Button icon="pi pi-comment" :label="t('runs.addComment')" severity="secondary" :disabled="!canWrite" @click="addRunComment" />
                </div>
                <div class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
                  <div v-for="comment in comments" :key="comment.id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
                    <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                      <span>{{ comment.author }}</span>
                      <Tag :value="comment.resolved ? t('common.completed') : t('common.pending')" :severity="comment.resolved ? 'success' : 'warn'" />
                    </div>
                    <small class="uno-text-[#6f8183]">{{ formatDateTime(comment.created_at) }}</small>
                    <p class="uno-mb-0 uno-mt-2">{{ comment.content }}</p>
                    <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                      <Button
                        icon="pi pi-check"
                        :label="comment.resolved ? t('runs.reopenComment') : t('runs.resolveComment')"
                        severity="secondary"
                        :disabled="!canWrite"
                        @click="toggleComment(comment)"
                      />
                      <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined :disabled="!canWrite" @click="deleteRunComment(comment.id)" />
                    </div>
                  </div>
                  <p v-if="!comments.length" class="uno-text-[#6f8183]">{{ t('runs.noComments') }}</p>
                </div>
              </template>
            </Card>

            <Card data-testid="run-detail-public-share-card">
              <template #title>{{ t('runs.publicShare') }}</template>
              <template #content>
                <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(180px,1fr))] uno-gap-[0.8rem]">
                  <label class="uno-grid uno-gap-[0.35rem]">
                    <span class="uno-text-[#6f8183]">{{ t('runs.shareTitle') }}</span>
                    <InputText v-model="shareForm.share_title" :placeholder="t('common.optional')" :disabled="!canWrite" />
                  </label>
                  <label class="uno-grid uno-gap-[0.35rem]">
                    <span class="uno-text-[#6f8183]">{{ t('runs.shareExpiryDays') }}</span>
                    <InputText v-model="shareForm.expires_in_days" type="number" :placeholder="t('common.optional')" :disabled="!canWrite" />
                  </label>
                </div>
                <Textarea v-model="shareForm.share_summary" rows="3" auto-resize :placeholder="t('runs.shareSummary')" class="uno-mt-3 uno-w-full" :disabled="!canWrite" />
                <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                  <Button
                    icon="pi pi-share-alt"
                    :label="currentPublicShare ? t('runs.updatePublicShare') : t('runs.createPublicShare')"
                    severity="secondary"
                    :disabled="!canWrite"
                    @click="savePublicShare"
                  />
                  <Button v-if="currentPublicShare" icon="pi pi-external-link" :label="t('common.open')" severity="secondary" @click="openPublicShare" />
                  <Button v-if="currentPublicShare" icon="pi pi-trash" :label="t('runs.deletePublicShare')" severity="danger" outlined :disabled="!canWrite" @click="deletePublicShare" />
                </div>
                <div v-if="currentPublicShare" class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
                  <div class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
                    <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                      <span class="uno-break-all">{{ currentPublicShare.url }}</span>
                      <Tag :value="String(currentPublicShare.view_count || 0)" severity="info" />
                    </div>
                    <small class="uno-text-[#6f8183]">{{ formatDateTime(currentPublicShare.expires_at) }}</small>
                  </div>
                </div>
              </template>
            </Card>
          </div>

          <details class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-4 uno-py-[0.85rem]">
            <summary class="uno-cursor-pointer uno-font-700">{{ t('runs.terminalOutput') }}</summary>
            <pre class="uno-m-0 uno-mt-3 uno-max-h-[460px] uno-overflow-auto uno-whitespace-pre-wrap uno-break-words uno-rounded-lg uno-bg-[#101b1d] uno-p-[0.85rem] uno-text-[#d8f3ee]">{{ terminalOutput || t('runs.noTerminalOutput') }}</pre>
          </details>

          <details data-testid="run-detail-timeline-card" class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-4 uno-py-[0.85rem]">
            <summary class="uno-cursor-pointer uno-font-700">{{ t('runs.timeline') }}</summary>
            <div v-if="timelineDisplayEvents.length" class="uno-mt-3 uno-grid uno-gap-3">
              <div class="uno-grid uno-gap-2 uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-[#fbfdfd] uno-p-3">
                <div class="uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
                  <strong class="uno-text-[#132a2d]">{{ t('runs.timelineSummary') }}</strong>
                  <span class="uno-text-sm uno-text-[#607174]">{{ t('runs.timelineCount', { count: timelineDisplayEvents.length }) }}</span>
                </div>
                <div class="uno-flex uno-flex-wrap uno-gap-2">
                  <Tag
                    v-for="item in timelineSummaryItems"
                    :key="item.label"
                    :value="`${item.label} · ${item.count}`"
                    severity="secondary"
                  />
                </div>
              </div>

              <details
                v-for="event in timelineDisplayEvents"
                :key="String(event.timestamp || '') + ':' + String(event.event || '')"
                class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-[#fbfdfd] uno-p-3"
              >
                <summary class="uno-flex uno-cursor-pointer uno-list-none uno-flex-wrap uno-items-start uno-justify-between uno-gap-3">
                  <div class="uno-grid uno-min-w-0 uno-gap-1">
                    <strong class="uno-text-[#132a2d]">{{ timelineEventLabel(event) }}</strong>
                    <p class="uno-m-0 uno-break-words uno-text-[#304345]">{{ timelineEventSummary(event) }}</p>
                  </div>
                  <div class="uno-grid uno-justify-items-end uno-gap-1">
                    <Tag :value="timelineEventLabel(event)" :severity="timelineEventSeverity(event)" />
                    <small class="uno-text-[#6f8183]">{{ formatDateTime(event.timestamp) }}</small>
                  </div>
                </summary>
                <pre class="uno-m-0 uno-mt-3 uno-max-h-[240px] uno-overflow-auto uno-whitespace-pre-wrap uno-break-words uno-rounded-lg uno-bg-white uno-p-3 uno-text-[#304345]">{{ timelineEventDetailText(event) }}</pre>
              </details>
            </div>
            <p v-else class="uno-m-0 uno-mt-3 uno-text-[#6f8183]">{{ t('runs.noTimeline') }}</p>
          </details>

          <details data-testid="run-detail-debates-card" class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-4 uno-py-[0.85rem]">
            <summary class="uno-cursor-pointer uno-font-700">{{ t('runs.debates') }}</summary>
            <div v-if="debateTranscripts.length" class="uno-mt-3 uno-grid uno-gap-3">
              <div class="uno-flex uno-flex-wrap uno-gap-2">
                <button
                  v-for="transcript in debateTranscripts"
                  :key="transcript.name"
                  type="button"
                  :class="[
                    'uno-min-h-9 uno-cursor-pointer uno-rounded-lg uno-border uno-px-3 uno-py-1.5 uno-text-sm',
                    selectedDebateTranscript?.name === transcript.name
                      ? 'uno-border-[#162326] uno-bg-[#162326] uno-text-white'
                      : 'uno-border-[#d5e2e2] uno-bg-white uno-text-[#304345] hover:uno-border-[#90a9aa]',
                  ]"
                  @click="selectedDebateName = transcript.name"
                >
                  {{ transcript.label }}
                </button>
              </div>

              <div v-if="selectedDebateTranscript" class="uno-grid uno-gap-3">
                <div class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-[#fbfdfd] uno-p-3">
                  <div class="uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
                    <strong class="uno-text-[#132a2d]">{{ selectedDebateTranscript.label }}</strong>
                    <span class="uno-text-sm uno-text-[#607174]">{{ t('runs.debateTurnCount', { count: selectedDebateTurns.length || 1 }) }}</span>
                  </div>
                </div>

                <div v-if="selectedDebateTurns.length" class="uno-grid uno-gap-3">
                  <div
                    v-for="(turn, index) in selectedDebateTurns"
                    :key="`${selectedDebateTranscript.name}-${index}`"
                    class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-[#fbfdfd] uno-p-3"
                  >
                    <div class="uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
                      <Tag :value="turn.speaker" severity="contrast" />
                      <small class="uno-text-[#6f8183]">{{ t('runs.debateTurnLabel', { count: index + 1 }) }}</small>
                    </div>
                    <p class="uno-m-0 uno-mt-2 uno-whitespace-pre-wrap uno-break-words uno-text-[#304345]">{{ turn.content }}</p>
                  </div>
                </div>
                <pre v-else class="uno-m-0 uno-max-h-[360px] uno-overflow-auto uno-whitespace-pre-wrap uno-break-words uno-rounded-lg uno-bg-[#fbfdfd] uno-p-3 uno-text-[#304345]">{{ selectedDebateTranscript.content }}</pre>
              </div>
            </div>
            <p v-else class="uno-m-0 uno-mt-3 uno-text-[#6f8183]">{{ t('runs.noDebates') }}</p>
          </details>

          <details data-testid="run-detail-debug-card" class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-4 uno-py-[0.85rem]">
            <summary class="uno-cursor-pointer uno-font-700">{{ t('runs.debugData') }}</summary>
            <div class="uno-mt-3 uno-grid uno-gap-3">
              <div class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-[#fbfdfd] uno-p-3">
                <strong class="uno-text-[#132a2d]">{{ t('runs.usageSummary') }}</strong>
                <pre class="uno-m-0 uno-mt-2 uno-max-h-[280px] uno-overflow-auto uno-whitespace-pre-wrap uno-break-words uno-rounded-lg uno-bg-white uno-p-3 uno-text-[#304345]">{{ usageSummaryText || t('runs.noUsageSummary') }}</pre>
              </div>
              <div class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-[#fbfdfd] uno-p-3">
                <strong class="uno-text-[#132a2d]">{{ t('runs.debugConfig') }}</strong>
                <pre class="uno-m-0 uno-mt-2 uno-max-h-[360px] uno-overflow-auto uno-whitespace-pre-wrap uno-break-words uno-rounded-lg uno-bg-white uno-p-3 uno-text-[#304345]">{{ debugConfigText || t('runs.noDebugConfig') }}</pre>
              </div>
              <div class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-[#fbfdfd] uno-p-3">
                <strong class="uno-text-[#132a2d]">{{ t('runs.fullState') }}</strong>
                <pre class="uno-m-0 uno-mt-2 uno-max-h-[420px] uno-overflow-auto uno-whitespace-pre-wrap uno-break-words uno-rounded-lg uno-bg-white uno-p-3 uno-text-[#304345]">{{ fullStateContent || t('runs.noFullState') }}</pre>
              </div>
            </div>
          </details>

          <details v-if="artifacts.length" class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-4 uno-py-[0.85rem]">
            <summary class="uno-cursor-pointer uno-font-700">{{ t('runs.artifacts') }}</summary>
            <div class="uno-mt-3 uno-flex uno-flex-wrap uno-gap-2">
              <a
                v-for="artifact in artifacts"
                :key="artifactName(artifact)"
                class="uno-inline-flex uno-min-h-[34px] uno-items-center uno-rounded-lg uno-border uno-border-[#d5e2e2] uno-px-[0.65rem] uno-py-1.5 uno-text-[#162326] uno-no-underline hover:uno-border-[#90a9aa] hover:uno-bg-[#f4f8f8]"
                :href="artifact.download_url"
              >{{ artifact.label }}</a>
            </div>
          </details>
        </div>
      </template>
    </Card>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import DatePicker from 'primevue/datepicker';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import OverlayBadge from 'primevue/overlaybadge';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import Textarea from 'primevue/textarea';
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import ReportMarkdown from '../components/ReportMarkdown.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPatch, apiPost, buildApiUrl } from '../services/api';
import { useSession } from '../stores/session';
import { formatDateTime, signalSeverity, type JsonRecord } from '../utils/format';
import { buildDecisionHighlights, buildInsightPanels } from '../utils/runDisplay';

type DebateTranscript = {
  name: string;
  label: string;
  content: string;
};

type DebateTurn = {
  speaker: string;
  content: string;
};

const SECTION_ORDER = [
  'market_report',
  'sentiment_report',
  'news_report',
  'fundamentals_report',
  'investment_plan',
  'trader_investment_plan',
  'final_trade_decision',
];
const FULL_STATE_ARTIFACT_NAME = 'full-state';

const DATA_SOURCE_LABELS: Record<string, string> = {
  alpha_vantage: 'Alpha Vantage',
  yfinance: 'Yahoo Finance',
  cn_stock: 'China A-share',
  cn_stock_em: 'Eastmoney',
  cn_stock_tx: 'Tencent',
  cn_fundamentals: 'China Fundamentals',
  cn_news: 'China News',
  cn_macro: 'China Macro',
  cn_market_signals: 'China Market Signals',
  fred: 'FRED',
  polymarket: 'Polymarket',
  stocktwits: 'StockTwits',
  reddit_rss: 'Reddit RSS',
};

const session = useSession();
const route = useRoute();
const router = useRouter();
const canWrite = computed(() => session.canWrite.value);
const selectedRun = ref<JsonRecord | null>(null);
const artifacts = ref<JsonRecord[]>([]);
const members = ref<JsonRecord[]>([]);
const pinnedRuns = ref<JsonRecord[]>([]);
const comments = ref<JsonRecord[]>([]);
const historyRuns = ref<JsonRecord[]>([]);
const historyPickerOpen = ref(false);
const timelineEvents = ref<JsonRecord[]>([]);
const debateTranscripts = ref<DebateTranscript[]>([]);
const selectedDebateName = ref('');
const debugConfig = ref<JsonRecord | null>(null);
const fullStateContent = ref('');
const terminalOutput = ref('');
const selectedSectionKey = ref('');
const commentBody = ref('');
const commentAuthor = ref('');
const error = ref('');
const { t } = useI18n();

const routeRunId = computed(() => {
  const value = route.params.runId;
  return Array.isArray(value) ? String(value[0] || '') : String(value || '');
});
const detailMetrics = computed(() => [
  { label: t('common.runId'), value: selectedRun.value?.run_id || t('common.na') },
  { label: t('common.ticker'), value: selectedRun.value?.ticker || t('common.na') },
  { label: t('common.provider'), value: selectedRun.value?.config_summary?.llm_provider || t('common.na') },
  { label: t('common.created'), value: formatDateTime(selectedRun.value?.created_at) },
]);
const runIdentityLabel = computed(() => {
  if (!selectedRun.value) {
    return '';
  }
  const companyName = String(selectedRun.value.company_name || '').trim();
  const ticker = String(selectedRun.value.ticker || '').trim();
  return companyName ? `${companyName} (${ticker})` : ticker;
});
const runHeaderTitle = computed(() => (
  selectedRun.value ? `${runIdentityLabel.value} · ${selectedRun.value.date}` : ''
));
const historyRunCount = computed(() => historyRuns.value.length);
const historyRunsByDate = computed(() => {
  const byDate = new Map<string, JsonRecord>();
  for (const run of historyRuns.value) {
    const date = String(run.date || '').trim();
    if (!date) {
      continue;
    }
    const current = byDate.get(date);
    if (!current || Number(run.created_at || 0) > Number(current.created_at || 0)) {
      byDate.set(date, run);
    }
  }
  return byDate;
});
const historyPickerValue = computed(() => dateFromRunDate(selectedRun.value?.date));
const historyMinDate = computed(() => {
  const runs = historyRuns.value
    .map((run) => dateFromRunDate(run.date))
    .filter((value): value is Date => value instanceof Date)
    .sort((left, right) => left.getTime() - right.getTime());
  return runs[0];
});
const historyMaxDate = computed(() => {
  const runs = historyRuns.value
    .map((run) => dateFromRunDate(run.date))
    .filter((value): value is Date => value instanceof Date)
    .sort((left, right) => right.getTime() - left.getTime());
  return runs[0];
});
const historyDisabledDates = computed(() => {
  if (!historyMinDate.value || !historyMaxDate.value) {
    return [];
  }
  const available = new Set(historyRunsByDate.value.keys());
  const disabled: Date[] = [];
  const cursor = new Date(historyMinDate.value);
  while (cursor.getTime() <= historyMaxDate.value.getTime()) {
    const runDate = runDateFromDate(cursor);
    if (!available.has(runDate)) {
      disabled.push(new Date(cursor));
    }
    cursor.setDate(cursor.getDate() + 1);
  }
  return disabled;
});
const debateArtifactLabels = computed<Record<string, string>>(() => ({
  'report-tree/2_research/bull.md': t('runs.debateBull'),
  'report-tree/2_research/bear.md': t('runs.debateBear'),
  'report-tree/2_research/manager.md': t('runs.debateResearchManager'),
  'report-tree/4_risk/aggressive.md': t('runs.debateAggressive'),
  'report-tree/4_risk/conservative.md': t('runs.debateConservative'),
  'report-tree/4_risk/neutral.md': t('runs.debateNeutral'),
}));
const orderedReportKeys = computed(() => {
  const sections = selectedRun.value?.report_sections || {};
  const keys = Object.keys(sections);
  return [
    ...SECTION_ORDER.filter((key) => keys.includes(key)),
    ...keys.filter((key) => !SECTION_ORDER.includes(key)),
  ];
});
const sectionOptions = computed(() => {
  if (!selectedRun.value) {
    return [];
  }
  const options = orderedReportKeys.value.map((key) => ({
    label: sectionLabel(key),
    value: key,
  }));
  if (selectedRun.value.final_report || selectedRun.value.current_report) {
    return [{ label: sectionLabel('overview'), value: 'overview' }, ...options];
  }
  return options;
});
const dataFetches = computed(() => {
  const value = selectedRun.value?.data_fetches;
  return Array.isArray(value) ? value as JsonRecord[] : [];
});
const dataWarnings = computed(() => {
  const value = selectedRun.value?.data_warnings;
  return Array.isArray(value) ? value as JsonRecord[] : [];
});
const timelineDisplayEvents = computed(() => [...timelineEvents.value].reverse());
const timelineSummaryItems = computed(() => {
  const counts = new Map<string, number>();
  for (const event of timelineDisplayEvents.value) {
    const label = timelineEventLabel(event);
    counts.set(label, (counts.get(label) || 0) + 1);
  }
  return Array.from(counts.entries()).map(([label, count]) => ({ label, count }));
});
const selectedDebateTranscript = computed(() => {
  if (!debateTranscripts.value.length) {
    return null;
  }
  return debateTranscripts.value.find((entry) => entry.name === selectedDebateName.value)
    || debateTranscripts.value[0];
});
const selectedDebateTurns = computed(() => parseDebateTranscript(selectedDebateTranscript.value?.content || ''));
const debugConfigText = computed(() => (
  debugConfig.value ? JSON.stringify(debugConfig.value, null, 2) : ''
));
const usageSummaryText = computed(() => {
  const value = selectedRun.value?.usage_summary;
  return value && typeof value === 'object' && !Array.isArray(value)
    ? JSON.stringify(value, null, 2)
    : '';
});
const selectedSectionText = computed(() => {
  if (!selectedRun.value) {
    return '';
  }
  if (selectedSectionKey.value === 'overview') {
    return selectedRun.value.final_report || selectedRun.value.current_report || '';
  }
  const sections = selectedRun.value.report_sections || {};
  return sections[selectedSectionKey.value] || '';
});
const decisionHighlights = computed(() => buildDecisionHighlights(
  selectedRun.value?.report_sections || {},
  selectedRun.value?.signal,
));
const decisionSummary = computed(() => (
  decisionHighlights.value.summary || t('runs.summaryFallback')
));
const decisionItems = computed(() => [
  {
    label: t('runs.finalRating'),
    value: decisionHighlights.value.finalRating || t('common.pending'),
  },
  {
    label: t('runs.tradeAction'),
    value: decisionHighlights.value.tradeAction || t('common.na'),
  },
  {
    label: t('runs.priceTarget'),
    value: decisionHighlights.value.priceTarget || t('common.na'),
  },
  {
    label: t('runs.riskControl'),
    value: decisionHighlights.value.riskControl || t('common.na'),
  },
]);
const insightActionLabels = computed(() => ({
  action: t('runs.actionLabel.action'),
  entry: t('runs.actionLabel.entry'),
  stopLoss: t('runs.actionLabel.stopLoss'),
  sizing: t('runs.actionLabel.sizing'),
}));
const insightPanels = computed(() => buildInsightPanels(
  selectedRun.value?.report_sections || {},
  insightActionLabels.value,
));
const memberOptions = computed(() => members.value.map((member) => ({
  label: String(member.name || member.id || ''),
  value: String(member.name || ''),
})));
const categoryOptions = computed(() => [
  { label: t('runs.pinCategoryHighConviction'), value: 'high-conviction' },
  { label: t('runs.pinCategoryFollowUp'), value: 'follow-up' },
  { label: t('runs.pinCategoryRisk'), value: 'risk' },
  { label: t('runs.pinCategoryArchive'), value: 'archive' },
]);
const priorityOptions = computed(() => [
  { label: 'P1', value: 'p1' },
  { label: 'P2', value: 'p2' },
  { label: 'P3', value: 'p3' },
]);
const actionStatusOptions = computed(() => [
  { label: t('runs.actionTodo'), value: 'todo' },
  { label: t('runs.actionDoing'), value: 'doing' },
  { label: t('runs.actionDone'), value: 'done' },
]);
const currentPinnedRun = computed(() => pinnedRuns.value.find((item) => item.run_id === selectedRun.value?.run_id) || null);
const currentPublicShare = computed(() => selectedRun.value?.public_share || null);
const canCancelRun = computed(() => {
  const status = String(selectedRun.value?.status || '').trim().toLowerCase();
  return status === 'queued' || status === 'running';
});
const pinForm = reactive({
  note: '',
  category: 'follow-up',
  priority: 'p2',
  next_action: '',
  action_status: 'todo',
  assignee: '',
  due_date: '',
});
const shareForm = reactive({
  expires_in_days: '',
  share_title: '',
  share_summary: '',
});
const ACTIVE_RUN_STATUSES = new Set(['queued', 'pending', 'running']);
const AUTO_REFRESH_INTERVAL_MS = 5000;
let autoRefreshTimer: ReturnType<typeof setTimeout> | null = null;
let autoRefreshInFlight = false;

function sectionLabel(key: string): string {
  switch (key) {
    case 'overview':
      return t('runs.section.overview');
    case 'market_report':
      return t('runs.section.market');
    case 'sentiment_report':
      return t('runs.section.sentiment');
    case 'news_report':
      return t('runs.section.news');
    case 'fundamentals_report':
      return t('runs.section.fundamentals');
    case 'investment_plan':
      return t('runs.section.research');
    case 'trader_investment_plan':
      return t('runs.section.trading');
    case 'final_trade_decision':
      return t('runs.section.decision');
    default:
      return key.replaceAll('_', ' ');
  }
}

function insightTitle(key: 'evidence' | 'risks' | 'actions'): string {
  switch (key) {
    case 'evidence':
      return t('runs.insight.evidence');
    case 'risks':
      return t('runs.insight.risks');
    case 'actions':
      return t('runs.insight.actions');
  }
}

function dataFetchItemLabel(entry: JsonRecord): string {
  return String(entry.item || entry.method || t('common.na'));
}

function artifactName(artifact: JsonRecord): string {
  return String(artifact.name || artifact.key || '').trim();
}

function artifactContentPath(encodedRunId: string, name: string): string {
  return `/api/runs/${encodedRunId}/artifacts/content?name=${encodeURIComponent(name)}`;
}

function dataFetchStatusLabel(entry: JsonRecord): string {
  switch (String(entry.status || '')) {
    case 'success':
      return t('runs.dataStatusSuccess');
    case 'fallback':
      return t('runs.dataStatusFallback');
    case 'unavailable':
      return t('runs.dataStatusUnavailable');
    case 'error':
      return t('runs.dataStatusError');
    case 'not_applicable':
      return t('runs.dataStatusNotApplicable');
    default:
      return String(entry.status || t('common.na'));
  }
}

function dataFetchStatusSeverity(entry: JsonRecord): string {
  switch (String(entry.status || '')) {
    case 'success':
      return 'success';
    case 'fallback':
      return 'warn';
    case 'unavailable':
    case 'error':
      return 'danger';
    case 'not_applicable':
      return 'info';
    default:
      return 'secondary';
  }
}

function dataFetchSourceLabel(source: unknown, status: unknown): string {
  const normalized = String(source || '').trim();
  if (!normalized) {
    return String(status) === 'not_applicable'
      ? t('runs.dataSourceNotApplicable')
      : t('common.na');
  }
  return DATA_SOURCE_LABELS[normalized] || normalized;
}

function dataFetchSourceList(value: unknown): string {
  if (!Array.isArray(value) || !value.length) {
    return t('common.na');
  }
  return value.map((item) => dataFetchSourceLabel(item, '')).join(' · ');
}

function timelineEventSeverity(event: JsonRecord): string {
  switch (String(event.event || '').trim()) {
    case 'complete':
    case 'report_update':
    case 'data_fetch':
      return 'success';
    case 'llm_call':
    case 'tool_call':
    case 'state_snapshot':
      return 'info';
    case 'data_warning':
    case 'cancelled':
      return 'warn';
    case 'error':
      return 'danger';
    default:
      return 'secondary';
  }
}

function timelineEventLabel(event: JsonRecord): string {
  switch (String(event.event || '').trim()) {
    case 'progress':
      return 'Progress';
    case 'agent_status':
      return 'Agent Status';
    case 'report_update':
      return 'Report Update';
    case 'llm_prompt':
      return 'LLM Prompt';
    case 'tool_call':
      return 'Tool Call';
    case 'data_fetch':
      return 'Data Fetch';
    case 'data_warning':
      return 'Data Warning';
    case 'state_snapshot':
      return 'State Snapshot';
    case 'terminal_output':
      return t('runs.terminalOutput');
    case 'complete':
      return t('common.completed');
    case 'cancelled':
      return t('common.cancelled');
    case 'error':
      return 'Error';
    default:
      return String(event.event || t('common.na'));
  }
}

function timelineEventSummary(event: JsonRecord): string {
  const data = event.data && typeof event.data === 'object' && !Array.isArray(event.data)
    ? event.data as JsonRecord
    : {};
  switch (String(event.event || '').trim()) {
    case 'progress':
      return String(data.message || data.tool_call || t('common.na'));
    case 'agent_status':
      return [String(data.agent || ''), String(data.status || '')].filter(Boolean).join(' ');
    case 'report_update':
      return [
        String(data.section ? sectionLabel(String(data.section)) : ''),
        typeof data.content_length === 'number' ? `${data.content_length} chars` : '',
      ].filter(Boolean).join(' · ') || String(data.content || t('common.na'));
    case 'llm_prompt':
      return [String(data.model || ''), String(data.prompt_preview || '')].filter(Boolean).join(' · ');
    case 'llm_call': {
      const tokens = typeof data.total_tokens === 'number' ? `${data.total_tokens} tokens` : '';
      return [String(data.model || ''), tokens, String(data.response_preview || '')].filter(Boolean).join(' · ');
    }
    case 'tool_call':
      return [String(data.name || ''), String(data.args_preview || '')].filter(Boolean).join(' · ');
    case 'data_fetch': {
      const item = String(data.item || data.method || t('common.na'));
      const source = dataFetchSourceLabel(data.actual_source, data.status);
      const status = dataFetchStatusLabel(data);
      const requestLabel = String(data.request_label || '').trim();
      const detail = String(data.detail || '').trim();
      const preview = String(data.result_preview || '').trim();
      return [item, requestLabel, `${source} [${status}]`, detail, preview].filter(Boolean).join(' · ');
    }
    case 'data_warning':
      return String(data.message || t('common.na'));
    case 'state_snapshot': {
      const chunkKeys = Array.isArray(data.chunk_keys) ? data.chunk_keys.join(', ') : '';
      const activeAgents = Array.isArray(data.in_progress_agents) ? data.in_progress_agents.join(', ') : '';
      const completed = typeof data.completed_agent_count === 'number' ? `${data.completed_agent_count} completed` : '';
      return [chunkKeys, activeAgents, completed].filter(Boolean).join(' · ');
    }
    case 'terminal_output':
      return String(data.line || data.stream || t('common.na'));
    case 'complete':
      return String(data.signal || t('common.completed'));
    case 'cancelled':
    case 'error':
      return String(data.message || t('common.na'));
    default:
      try {
        return JSON.stringify(data, null, 2);
      } catch {
        return t('common.na');
      }
  }
}

function timelineEventDetailText(event: JsonRecord): string {
  const data = event.data && typeof event.data === 'object' && !Array.isArray(event.data)
    ? event.data as JsonRecord
    : {};
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data || '');
  }
}

function parseDebateTranscript(content: string): DebateTurn[] {
  const lines = content
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  const turns: DebateTurn[] = [];
  for (const line of lines) {
    const match = line.match(/^([^:]{1,80}):\s*(.+)$/);
    if (!match) {
      if (turns.length) {
        const current = turns[turns.length - 1];
        current.content = `${current.content}\n${line}`;
      }
      continue;
    }
    turns.push({
      speaker: match[1].trim(),
      content: match[2].trim(),
    });
  }
  return turns;
}

async function fetchArtifactContent(encodedRunId: string, name: string): Promise<string | null> {
  try {
    const payload = await apiGet<JsonRecord>(artifactContentPath(encodedRunId, name), session.apiContext.value);
    return typeof payload.content === 'string' ? payload.content : null;
  } catch {
    return null;
  }
}

async function loadDebateTranscripts(encodedRunId: string, artifactRows: JsonRecord[]): Promise<DebateTranscript[]> {
  const entries = Object.entries(debateArtifactLabels.value).filter(([name]) => (
    artifactRows.some((artifact) => artifactName(artifact) === name)
  ));
  const loaded = await Promise.all(entries.map(async ([name, label]) => {
    const content = await fetchArtifactContent(encodedRunId, name);
    if (!content) {
      return null;
    }
    return { name, label, content };
  }));
  return loaded.filter((entry): entry is DebateTranscript => entry !== null);
}

async function loadFullStateContent(encodedRunId: string, artifactRows: JsonRecord[]): Promise<string> {
  if (!artifactRows.some((artifact) => artifactName(artifact) === FULL_STATE_ARTIFACT_NAME)) {
    return '';
  }
  return await fetchArtifactContent(encodedRunId, FULL_STATE_ARTIFACT_NAME) || '';
}

async function loadRunDetail(options: { silent?: boolean } = {}) {
  if (!routeRunId.value) return;
  const { silent = false } = options;
  error.value = '';
  if (!silent) {
    selectedRun.value = null;
    artifacts.value = [];
    historyRuns.value = [];
    historyPickerOpen.value = false;
    timelineEvents.value = [];
    debateTranscripts.value = [];
    selectedDebateName.value = '';
    debugConfig.value = null;
    fullStateContent.value = '';
    terminalOutput.value = '';
    selectedSectionKey.value = '';
  }
  try {
    const encodedRunId = encodeURIComponent(routeRunId.value);
    selectedRun.value = await apiGet<JsonRecord>(`/api/runs/${encodedRunId}`, session.apiContext.value);
    if (!shouldAutoRefreshRun(selectedRun.value?.status)) {
      stopAutoRefresh();
    }
    const hasOverview = Boolean(selectedRun.value.final_report || selectedRun.value.current_report);
    if (!silent || !selectedSectionKey.value) {
      selectedSectionKey.value = hasOverview ? 'overview' : orderedReportKeys.value[0] || '';
    }
    const [artifactRows, output, pinnedItems, commentItems, memberItems, runRows, timelineRows, debugPayload] = await Promise.all([
      apiGet<JsonRecord[]>(`/api/runs/${encodedRunId}/artifacts`, session.apiContext.value),
      loadTerminalOutput(encodedRunId),
      apiGet<JsonRecord[]>('/api/pinned-runs', session.apiContext.value),
      apiGet<JsonRecord[]>(`/api/runs/${encodedRunId}/comments`, session.apiContext.value),
      apiGet<JsonRecord[]>('/api/members', session.apiContext.value),
      apiGet<JsonRecord[]>('/api/runs', session.apiContext.value),
      apiGet<JsonRecord[]>(`/api/runs/${encodedRunId}/timeline`, session.apiContext.value),
      apiGet<JsonRecord>(`/api/runs/${encodedRunId}/debug-config`, session.apiContext.value),
    ]);
    artifacts.value = artifactRows;
    terminalOutput.value = output;
    timelineEvents.value = Array.isArray(timelineRows) ? timelineRows : [];
    debugConfig.value = debugPayload && typeof debugPayload === 'object' && !Array.isArray(debugPayload)
      ? debugPayload
      : null;
    pinnedRuns.value = pinnedItems;
    comments.value = commentItems;
    members.value = memberItems;
    historyRuns.value = runRows
      .filter((item) => String(item.ticker || '').trim().toUpperCase() === String(selectedRun.value?.ticker || '').trim().toUpperCase())
      .sort((left, right) => Number(right.created_at || 0) - Number(left.created_at || 0));
    commentAuthor.value = session.state.currentMemberId
      ? (memberItems.find((item) => item.id === session.state.currentMemberId)?.name || '')
      : '';
    [debateTranscripts.value, fullStateContent.value] = await Promise.all([
      loadDebateTranscripts(encodedRunId, artifactRows),
      loadFullStateContent(encodedRunId, artifactRows),
    ]);
    if (!selectedDebateName.value || !debateTranscripts.value.some((entry) => entry.name === selectedDebateName.value)) {
      selectedDebateName.value = debateTranscripts.value[0]?.name || '';
    }
    hydratePinForm();
    hydrateShareForm();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('runs.loadError');
  }
}

function normalizedRunStatus(status: unknown): string {
  return String(status || '').trim().toLowerCase();
}

function shouldAutoRefreshRun(status: unknown): boolean {
  return ACTIVE_RUN_STATUSES.has(normalizedRunStatus(status));
}

function stopAutoRefresh() {
  if (autoRefreshTimer !== null) {
    clearTimeout(autoRefreshTimer);
    autoRefreshTimer = null;
  }
}

async function refreshRunningRun() {
  if (autoRefreshInFlight) {
    return;
  }
  if (!shouldAutoRefreshRun(selectedRun.value?.status)) {
    stopAutoRefresh();
    return;
  }

  autoRefreshInFlight = true;
  try {
    await loadRunDetail({ silent: true });
  } finally {
    autoRefreshInFlight = false;
    if (shouldAutoRefreshRun(selectedRun.value?.status)) {
      ensureAutoRefresh();
    } else {
      stopAutoRefresh();
    }
  }
}

function ensureAutoRefresh() {
  if (!shouldAutoRefreshRun(selectedRun.value?.status)) {
    stopAutoRefresh();
    return;
  }
  if (autoRefreshTimer !== null) {
    return;
  }
  autoRefreshTimer = setTimeout(() => {
    autoRefreshTimer = null;
    void refreshRunningRun();
  }, AUTO_REFRESH_INTERVAL_MS);
}

function hydratePinForm() {
  const current = currentPinnedRun.value;
  if (!current) {
    Object.assign(pinForm, {
      note: '',
      category: 'follow-up',
      priority: 'p2',
      next_action: '',
      action_status: 'todo',
      assignee: '',
      due_date: '',
    });
    return;
  }
  Object.assign(pinForm, {
    note: current.note || '',
    category: current.category || 'follow-up',
    priority: current.priority || 'p2',
    next_action: current.next_action || '',
    action_status: current.action_status || 'todo',
    assignee: current.assignee || '',
    due_date: current.due_date || '',
  });
}

function hydrateShareForm() {
  const current = currentPublicShare.value;
  Object.assign(shareForm, {
    expires_in_days: '',
    share_title: current?.share_title || '',
    share_summary: current?.share_summary || '',
  });
}

async function loadTerminalOutput(encodedRunId: string) {
  const response = await fetch(buildApiUrl(`/api/runs/${encodedRunId}/terminal-output`, session.apiContext.value), {
    credentials: 'same-origin',
  });
  if (!response.ok) {
    throw new Error(response.statusText || t('runs.terminalOutputLoadError'));
  }
  return response.text();
}

async function retryRun() {
  if (!selectedRun.value?.run_id) return;
  const runStatus = String(selectedRun.value.status || '').trim().toLowerCase();
  if (runStatus === 'completed') {
    const runLabel = runIdentityLabel.value || String(selectedRun.value.ticker || '').trim();
    const confirmed = window.confirm(
      t('runs.retryCompletedConfirm', {
        run: runLabel,
        date: String(selectedRun.value.date || ''),
      }),
    );
    if (!confirmed) {
      return;
    }
  }
  const created = await apiPost<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/retry`,
    {},
    session.apiContext.value,
  );
  if (created.run_id) {
    await router.push({ name: 'run-detail', params: { runId: String(created.run_id) } });
    return;
  }
  selectedRun.value = created;
  terminalOutput.value = '';
}

async function cancelRun() {
  if (!selectedRun.value?.run_id) return;
  await apiPost(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/cancel`,
    {},
    session.apiContext.value,
  );
  await loadRunDetail({ silent: true });
}

async function deleteRun() {
  if (!selectedRun.value?.run_id) return;
  await apiDelete(`/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}`, session.apiContext.value);
  await router.push('/runs');
}

async function savePinnedRun() {
  if (!selectedRun.value?.run_id) return;
  await apiPost<JsonRecord>('/api/pinned-runs', {
    run_id: selectedRun.value.run_id,
    note: pinForm.note || null,
    category: pinForm.category || null,
    priority: pinForm.priority || null,
    next_action: pinForm.next_action || null,
    action_status: pinForm.action_status || null,
    assignee: pinForm.assignee || null,
    due_date: pinForm.due_date || null,
  }, session.apiContext.value);
  pinnedRuns.value = await apiGet<JsonRecord[]>('/api/pinned-runs', session.apiContext.value);
  hydratePinForm();
}

async function deletePinnedRun() {
  if (!selectedRun.value?.run_id) return;
  await apiDelete(`/api/pinned-runs/${encodeURIComponent(String(selectedRun.value.run_id))}`, session.apiContext.value);
  pinnedRuns.value = await apiGet<JsonRecord[]>('/api/pinned-runs', session.apiContext.value);
  hydratePinForm();
}

async function savePublicShare() {
  if (!selectedRun.value?.run_id) return;
  const runId = encodeURIComponent(String(selectedRun.value.run_id));
  if (!currentPublicShare.value) {
    await apiPost<JsonRecord>(`/api/runs/${runId}/public-share`, {}, session.apiContext.value);
  }
  const updatedShare = await apiPatch<JsonRecord>(
    `/api/runs/${runId}/public-share`,
    {
      expires_in_days: shareForm.expires_in_days === '' ? null : Number(shareForm.expires_in_days),
      share_title: shareForm.share_title || null,
      share_summary: shareForm.share_summary || null,
    },
    session.apiContext.value,
  );
  selectedRun.value = {
    ...selectedRun.value,
    public_share: updatedShare,
  };
  hydrateShareForm();
}

function openPublicShare() {
  if (!currentPublicShare.value?.url) return;
  window.open(currentPublicShare.value.url, '_blank', 'noopener');
}

async function deletePublicShare() {
  if (!selectedRun.value?.run_id) return;
  await apiDelete(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/public-share`,
    session.apiContext.value,
  );
  selectedRun.value = await apiGet<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}`,
    session.apiContext.value,
  );
  hydrateShareForm();
}

async function addRunComment() {
  if (!selectedRun.value?.run_id || !commentAuthor.value || !commentBody.value.trim()) return;
  await apiPost<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments`,
    {
      author: commentAuthor.value,
      content: commentBody.value.trim(),
    },
    session.apiContext.value,
  );
  commentBody.value = '';
  comments.value = await apiGet<JsonRecord[]>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments`,
    session.apiContext.value,
  );
}

async function toggleComment(comment: JsonRecord) {
  if (!selectedRun.value?.run_id) return;
  const resolver = comment.resolved ? null : (commentAuthor.value || comment.author);
  await apiPatch<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments/${encodeURIComponent(String(comment.id))}`,
    {
      resolved: !comment.resolved,
      resolved_by: resolver,
    },
    session.apiContext.value,
  );
  comments.value = await apiGet<JsonRecord[]>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments`,
    session.apiContext.value,
  );
}

async function deleteRunComment(commentId: string) {
  if (!selectedRun.value?.run_id) return;
  await apiDelete(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments/${encodeURIComponent(commentId)}`,
    session.apiContext.value,
  );
  comments.value = await apiGet<JsonRecord[]>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments`,
    session.apiContext.value,
  );
}

async function handleHistoryDateSelect(value: Date | Date[] | (Date | null)[] | null | undefined) {
  if (!(value instanceof Date) || !selectedRun.value?.run_id) {
    return;
  }
  const selectedDate = runDateFromDate(value);
  const matched = historyRunsByDate.value.get(selectedDate);
  if (!matched?.run_id) {
    error.value = t('runs.historyUnavailable');
    return;
  }
  historyPickerOpen.value = false;
  if (String(matched.run_id) === String(selectedRun.value.run_id)) {
    return;
  }
  await router.push({ name: 'run-detail', params: { runId: String(matched.run_id) } });
}

function dateFromRunDate(value: unknown): Date | null {
  if (typeof value !== 'string') {
    return null;
  }
  const match = value.trim().match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return null;
  }
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

function runDateFromDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function goBack() {
  void router.push('/runs');
}

watch(() => selectedRun.value?.status, (status) => {
  if (shouldAutoRefreshRun(status)) {
    ensureAutoRefresh();
    return;
  }
  stopAutoRefresh();
});

watch(routeRunId, () => {
  stopAutoRefresh();
  void loadRunDetail();
}, { immediate: true });

onBeforeUnmount(() => {
  stopAutoRefresh();
});
</script>
