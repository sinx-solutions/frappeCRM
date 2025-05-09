<template>
  <TextEditor
    ref="textEditor"
    :editor-class="[
      'prose-sm max-w-none',
      editable && 'min-h-[7rem]',
      '[&_p.reply-to-content]:hidden',
    ]"
    :content="content"
    @change="editable ? (content = $event) : null"
    :starterkit-options="{
      heading: { levels: [2, 3, 4, 5, 6] },
      paragraph: false,
    }"
    :placeholder="placeholder"
    :editable="editable"
    :extensions="[CustomParagraph]"
  >
    <template #top>
      <div class="flex flex-col gap-3">
        <div class="sm:mx-10 mx-4 flex items-center gap-2 border-t pt-2.5">
          <span class="text-xs text-ink-gray-4">{{ __('TO') }}:</span>
          <MultiSelectEmailInput
            class="flex-1"
            variant="ghost"
            v-model="toEmails"
            :validate="validateEmail"
            :error-message="
              (value) => __('{0} is an invalid email address', [value])
            "
          />
          <div class="flex gap-1.5">
            <Button
              :label="__('CC')"
              variant="ghost"
              @click="toggleCC()"
              :class="[
                cc
                  ? '!bg-surface-gray-4 hover:bg-surface-gray-3'
                  : '!text-ink-gray-4',
              ]"
            />
            <Button
              :label="__('BCC')"
              variant="ghost"
              @click="toggleBCC()"
              :class="[
                bcc
                  ? '!bg-surface-gray-4 hover:bg-surface-gray-3'
                  : '!text-ink-gray-4',
              ]"
            />
          </div>
        </div>
        <div v-if="cc" class="sm:mx-10 mx-4 flex items-center gap-2">
          <span class="text-xs text-ink-gray-4">{{ __('CC') }}:</span>
          <MultiSelectEmailInput
            ref="ccInput"
            class="flex-1"
            variant="ghost"
            v-model="ccEmails"
            :validate="validateEmail"
            :error-message="
              (value) => __('{0} is an invalid email address', [value])
            "
          />
        </div>
        <div v-if="bcc" class="sm:mx-10 mx-4 flex items-center gap-2">
          <span class="text-xs text-ink-gray-4">{{ __('BCC') }}:</span>
          <MultiSelectEmailInput
            ref="bccInput"
            class="flex-1"
            variant="ghost"
            v-model="bccEmails"
            :validate="validateEmail"
            :error-message="
              (value) => __('{0} is an invalid email address', [value])
            "
          />
        </div>
        <div class="sm:mx-10 mx-4 flex items-center gap-2 pb-2.5">
          <span class="text-xs text-ink-gray-4">{{ __('SUBJECT') }}:</span>
          <input
            class="flex-1 border-none text-ink-gray-9 text-base bg-surface-white hover:bg-surface-white focus:border-none focus:!shadow-none focus-visible:!ring-0"
            v-model="subject"
          />
        </div>
      </div>
    </template>
    <template v-slot:editor="{ editor }">
      <EditorContent
        :class="[
          editable &&
            'sm:mx-10 mx-4 max-h-[35vh] overflow-y-auto border-t py-3',
        ]"
        :editor="editor"
      />
    </template>
    <template v-slot:bottom>
      <div v-if="editable" class="flex flex-col gap-2">
        <div class="flex flex-wrap gap-2 sm:px-10 px-4">
          <AttachmentItem
            v-for="a in attachments"
            :key="a.file_url"
            :label="a.file_name"
          >
            <template #suffix>
              <FeatherIcon
                class="h-3.5"
                name="x"
                @click.stop="removeAttachment(a)"
              />
            </template>
          </AttachmentItem>
        </div>
        <div
          class="flex justify-between gap-2 overflow-hidden border-t sm:px-10 px-4 py-2.5"
        >
          <div class="flex gap-1 items-center overflow-x-auto">
            <TextEditorBubbleMenu :buttons="textEditorMenuButtons" />
            <IconPicker
              v-model="emoji"
              v-slot="{ togglePopover }"
              @update:modelValue="() => appendEmoji()"
            >
              <Button variant="ghost" @click="togglePopover()">
                <template #icon>
                  <SmileIcon class="h-4" />
                </template>
              </Button>
            </IconPicker>
            <FileUploader
              :upload-args="{
                doctype: doctype,
                docname: modelValue.name,
                private: true,
              }"
              @success="(f) => attachments.push(f)"
            >
              <template #default="{ openFileSelector }">
                <Button variant="ghost" @click="openFileSelector()">
                  <template #icon>
                    <AttachmentIcon class="h-4" />
                  </template>
                </Button>
              </template>
            </FileUploader>
            <Button
              variant="ghost"
              @click="showEmailTemplateSelectorModal = true"
            >
              <template #icon>
                <Email2Icon class="h-4" />
              </template>
            </Button>
            <Button
              variant="ghost"
              @click="showAIEmailGeneratorModal = true"
              v-if="doctype === 'CRM Lead'"
            >
              <template #icon>
                <AIEmailIcon class="h-4" />
              </template>
              <template #label>
                {{ __('AI') }}
              </template>
            </Button>
          </div>
          <div class="mt-2 flex items-center justify-end space-x-2 sm:mt-0">
            <Button v-bind="discardButtonProps || {}" :label="__('Discard')" />
            <Button
              variant="solid"
              v-bind="submitButtonProps || {}"
              :label="__('Send')"
            />
          </div>
        </div>
      </div>
    </template>
  </TextEditor>
  <EmailTemplateSelectorModal
    v-model="showEmailTemplateSelectorModal"
    :doctype="doctype"
    @apply="applyEmailTemplate"
  />
  <AIEmailGeneratorModal
    v-model="showAIEmailGeneratorModal"
    :lead="modelValue"
    @apply="applyAIGeneratedEmail"
  />
</template>

<script setup>
import IconPicker from '@/components/IconPicker.vue'
import SmileIcon from '@/components/Icons/SmileIcon.vue'
import Email2Icon from '@/components/Icons/Email2Icon.vue'
import AIEmailIcon from '@/components/Icons/AIEmailIcon.vue'
import AttachmentIcon from '@/components/Icons/AttachmentIcon.vue'
import AttachmentItem from '@/components/AttachmentItem.vue'
import MultiSelectEmailInput from '@/components/Controls/MultiSelectEmailInput.vue'
import EmailTemplateSelectorModal from '@/components/Modals/EmailTemplateSelectorModal.vue'
import AIEmailGeneratorModal from '@/components/Modals/AIEmailGeneratorModal.vue'
import { TextEditorBubbleMenu, TextEditor, FileUploader, call } from 'frappe-ui'
import { capture } from '@/telemetry'
import { validateEmail } from '@/utils'
import Paragraph from '@tiptap/extension-paragraph'
import { EditorContent } from '@tiptap/vue-3'
import { ref, computed, nextTick, onMounted } from 'vue'

const props = defineProps({
  placeholder: {
    type: String,
    default: null,
  },
  editable: {
    type: Boolean,
    default: true,
  },
  doctype: {
    type: String,
    default: 'CRM Lead',
  },
  subject: {
    type: String,
    default: '',
  },
  editorProps: {
    type: Object,
    default: () => ({}),
  },
  submitButtonProps: {
    type: Object,
    default: () => ({}),
  },
  discardButtonProps: {
    type: Object,
    default: () => ({}),
  },
})

const CustomParagraph = Paragraph.extend({
  addAttributes() {
    return {
      class: {
        default: null,
        renderHTML: (attributes) => {
          if (!attributes.class) {
            return {}
          }
          return {
            class: `${attributes.class}`,
          }
        },
      },
    }
  },
})

const modelValue = defineModel()
const attachments = defineModel('attachments')
const content = defineModel('content')

const textEditor = ref(null)
const cc = ref(false)
const bcc = ref(false)
const emoji = ref('')
const isAIGenerated = ref(false)

const subject = ref(props.subject)
const toEmails = ref(modelValue.value.email ? [modelValue.value.email] : [])
const ccEmails = ref([])
const bccEmails = ref([])
const ccInput = ref(null)
const bccInput = ref(null)

const showEmailTemplateSelectorModal = ref(false)
const showAIEmailGeneratorModal = ref(false)

const selectedTemplateName = ref(null)

const editor = computed(() => {
  return textEditor.value.editor
})

function removeAttachment(attachment) {
  attachments.value = attachments.value.filter((a) => a !== attachment)
}

function applyAIGeneratedEmail(emailData) {
  console.log("[EmailEditor] applyAIGeneratedEmail called", emailData);
  if (emailData.subject) {
    subject.value = emailData.subject
  }
  if (emailData.content) {
    content.value = emailData.content // Update the editor content
    if (editor.value && editor.value.commands) {
       editor.value.commands.setContent(emailData.content, true);
    } else {
       console.error("Editor commands not available to set AI content");
    }
    isAIGenerated.value = true
    selectedTemplateName.value = null // Clear selected template if AI populates editor
    console.log("[EmailEditor] AI content applied, selectedTemplateName cleared.");
  }
  capture('ai_email_applied', { doctype: props.doctype })
}

function applyEmailTemplate(template) {
  console.log('[EmailEditor] applyEmailTemplate called with raw template:', JSON.parse(JSON.stringify(template)));
  if (template && template.name) {
    selectedTemplateName.value = template.name;
    subject.value = template.subject || props.subject; // Use template subject as preview in subject field
    
    // Get the actual template content to display in the editor
    const templateContent = template.use_html ? template.response_html : template.response;
    
    // Format the content with a note at the top that this is a template
    const editorContent = `<p><i><b>Template:</b> ${template.name}</i></p><hr />${templateContent}`;
    content.value = editorContent; 
    
    // Set the editor content with the actual template for preview
    if (textEditor.value && textEditor.value.editor) {
      console.log('[EmailEditor] Setting editor content with actual template content');
      try {
        textEditor.value.editor.commands.setContent(editorContent, true);
        console.log('[EmailEditor] Successfully set editor content with template');
      } catch (error) {
        console.error('[EmailEditor] Error setting template content:', error);
        // Fallback method
        try {
          textEditor.value.editor.commands.clearContent();
          textEditor.value.editor.commands.insertContent(editorContent);
          console.log('[EmailEditor] Set template content via fallback method');
        } catch (fallbackError) {
          console.error('[EmailEditor] Fallback method for template content also failed:', fallbackError);
        }
      }
    } else {
      console.error('[EmailEditor] Editor reference not available for template content');
    }
    
    isAIGenerated.value = false; // Reset AI flag
    console.log(`[EmailEditor] Stored selectedTemplateName: ${selectedTemplateName.value}. Template content displayed in editor.`);
  } else {
    console.error('[EmailEditor] applyEmailTemplate called with invalid template object:', template);
    selectedTemplateName.value = null;
  }
  showEmailTemplateSelectorModal.value = false;
}

function appendEmoji() {
  editor.value.commands.insertContent(emoji.value)
  editor.value.commands.focus()
  emoji.value = ''
  capture('emoji_inserted_in_email', { emoji: emoji.value })
}

function toggleCC() {
  cc.value = !cc.value
  cc.value && nextTick(() => ccInput.value.setFocus())
}

function toggleBCC() {
  bcc.value = !bcc.value
  bcc.value && nextTick(() => bccInput.value.setFocus())
}

onMounted(() => {
  // No email service preference code here
})

defineExpose({
  editor,
  subject,
  content,
  cc,
  bcc,
  toEmails,
  ccEmails,
  bccEmails,
  isAIGenerated,
  selectedTemplateName
})

const textEditorMenuButtons = [
  'Paragraph',
  ['Heading 2', 'Heading 3', 'Heading 4', 'Heading 5', 'Heading 6'],
  'Separator',
  'Bold',
  'Italic',
  'Separator',
  'Bullet List',
  'Numbered List',
  'Separator',
  'Align Left',
  'Align Center',
  'Align Right',
  'FontColor',
  'Separator',
  'Image',
  'Video',
  'Link',
  'Blockquote',
  'Code',
  'Horizontal Rule',
  [
    'InsertTable',
    'AddColumnBefore',
    'AddColumnAfter',
    'DeleteColumn',
    'AddRowBefore',
    'AddRowAfter',
    'DeleteRow',
    'MergeCells',
    'SplitCell',
    'ToggleHeaderColumn',
    'ToggleHeaderRow',
    'ToggleHeaderCell',
    'DeleteTable',
  ],
]
</script>
