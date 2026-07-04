import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/card_renderer.dart';

class StudyScreen extends StatefulWidget {
  const StudyScreen({super.key});

  @override
  State<StudyScreen> createState() => _StudyScreenState();
}

class _StudyScreenState extends State<StudyScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final List<_ChatMsg> _messages = [];
  bool _isLoading = false;
  Map<String, dynamic>? _lastResult;

  Future<void> _send(String text) async {
    if (text.trim().isEmpty) return;
    final student = context.read<AuthProvider>().student!;
    setState(() {
      _messages.add(_ChatMsg(text: text, isUser: true));
      _isLoading = true;
    });
    _controller.clear();
    try {
      final result = await ApiService().sendMessage(student.studentId, text);
      // Chat bubble preview — plain text extracted from whatever card type was returned
      final preview = result['notes'] as String? ??
          result['response'] as String? ??
          result['summary'] as String? ??
          result['message'] as String? ?? '';
      final previewShort = preview.length > 280
          ? '${preview.substring(0, 280)}…'
          : preview;
      setState(() {
        _messages.add(_ChatMsg(text: previewShort, isUser: false, richResult: result));
        _lastResult = result;
      });
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollController.hasClients) {
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });
    } catch (e) {
      setState(() => _messages.add(_ChatMsg(text: 'Error: $e', isUser: false, isError: true)));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final lang = context.watch<AuthProvider>().student?.preferredLanguage ?? 'en';

    return Column(
      children: [
        Expanded(
          child: _messages.isEmpty
              ? _WelcomePanel(lang: lang, onTopicTap: _send)
              : ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(16),
                  itemCount: _messages.length,
                  itemBuilder: (_, i) => _BubbleWidget(msg: _messages[i], lang: lang),
                ),
        ),
        // A2UI rich card panel — rendered below chat when a result is available
        if (_lastResult != null && _lastResult!.containsKey('_card_type'))
          Container(
            constraints: const BoxConstraints(maxHeight: 420),
            color: Colors.grey.shade50,
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(12),
              child: _VibeDiffConfirmWrapper(
                result: _lastResult!,
                lang: lang,
                studentId: context.read<AuthProvider>().student?.studentId ?? '',
                onConfirmed: () => setState(() => _lastResult = null),
              ),
            ),
          ),
        if (_isLoading)
          const LinearProgressIndicator(minHeight: 2, color: AppTheme.primary),
        _InputBar(controller: _controller, onSend: _send, lang: lang),
      ],
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}

class _WelcomePanel extends StatelessWidget {
  final String lang;
  final ValueChanged<String> onTopicTap;
  const _WelcomePanel({required this.lang, required this.onTopicTap});

  static const _suggestions = [
    'Explain Algebra basics', 'What is Photosynthesis?',
    'Newton\'s Laws of Motion', 'How does Compound Interest work?',
  ];
  static const _suggestionsHi = [
    'बीजगणित की मूल बातें समझाएं', 'प्रकाश संश्लेषण क्या है?',
    'न्यूटन के गति के नियम', 'चक्रवृद्धि ब्याज कैसे काम करता है?',
  ];

  @override
  Widget build(BuildContext context) {
    final suggestions = lang == 'hi' ? _suggestionsHi : _suggestions;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const SizedBox(height: 24),
        const Center(child: Text('📖', style: TextStyle(fontSize: 64))),
        const SizedBox(height: 16),
        Center(child: Text(
          lang == 'hi' ? 'VidyaBot से कुछ भी पूछें' : 'Ask VidyaBot anything',
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: AppTheme.primary),
        )),
        Center(child: Text(
          lang == 'hi' ? 'अपने पाठ्यक्रम से किसी भी विषय पर नोट्स पाएं'
                       : 'Get notes on any topic from your syllabus',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey.shade600),
        )),
        const SizedBox(height: 24),
        Text(lang == 'hi' ? 'सुझाए गए विषय:' : 'Try asking about:',
            style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 12),
        ...suggestions.map((s) => Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: const Icon(Icons.lightbulb_outline, color: AppTheme.secondary),
            title: Text(s),
            trailing: const Icon(Icons.arrow_forward_ios, size: 14),
            onTap: () => onTopicTap(s),
          ),
        )),
      ],
    );
  }
}

class _BubbleWidget extends StatelessWidget {
  final _ChatMsg msg;
  final String lang;
  const _BubbleWidget({required this.msg, required this.lang});

  @override
  Widget build(BuildContext context) {
    if (msg.isUser) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.only(bottom: 12, left: 60),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppTheme.primary,
            borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
          ),
          child: Text(msg.text, style: const TextStyle(color: Colors.white)),
        ),
      );
    }
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12, right: 60),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: msg.isError ? const Color(0xFFFFEBEE) : Colors.white,
          borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4)],
        ),
        child: msg.text.length > 200
            ? MarkdownBody(data: msg.text, shrinkWrap: true)
            : Text(msg.text),
      ),
    );
  }
}

/// Wraps CardRenderer and adds a Confirm button for vibe_diff_card.
class _VibeDiffConfirmWrapper extends StatefulWidget {
  final Map<String, dynamic> result;
  final String lang;
  final String studentId;
  final VoidCallback onConfirmed;

  const _VibeDiffConfirmWrapper({
    required this.result,
    required this.lang,
    required this.studentId,
    required this.onConfirmed,
  });

  @override
  State<_VibeDiffConfirmWrapper> createState() => _VibeDiffConfirmWrapperState();
}

class _VibeDiffConfirmWrapperState extends State<_VibeDiffConfirmWrapper> {
  bool _confirming = false;

  Future<void> _confirm() async {
    final pending = widget.result['pending_action'] as Map<String, dynamic>? ?? {};
    final token = pending['token'] as String? ?? '';
    final action = pending['action_name'] as String? ?? '';
    if (token.isEmpty) return;

    setState(() => _confirming = true);
    try {
      final route = action.contains('calendar') ? 'schedule' : 'digest';
      await ApiService().confirmAction(widget.studentId, route, token);
      widget.onConfirmed();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _confirming = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isVibeDiff = widget.result['_card_type'] == 'vibe_diff_card';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CardRenderer(result: widget.result, lang: widget.lang),
        if (isVibeDiff) ...[
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: _confirming ? null : _confirm,
                icon: _confirming
                    ? const SizedBox(width: 16, height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.check),
                label: Text(widget.lang == 'hi' ? 'पुष्टि करें' : 'Confirm'),
                style: FilledButton.styleFrom(backgroundColor: AppTheme.primary),
              ),
            ),
          ]),
        ],
      ],
    );
  }
}

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String> onSend;
  final String lang;
  const _InputBar({required this.controller, required this.onSend, required this.lang});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      color: Colors.white,
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              decoration: InputDecoration(
                hintText: lang == 'hi' ? 'कोई भी प्रश्न पूछें...' : 'Ask any question...',
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
              onSubmitted: onSend,
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            onPressed: () => onSend(controller.text),
            icon: const Icon(Icons.send),
            style: IconButton.styleFrom(backgroundColor: AppTheme.primary),
          ),
        ],
      ),
    );
  }
}

class _ChatMsg {
  final String text;
  final bool isUser;
  final bool isError;
  final Map<String, dynamic>? richResult;
  const _ChatMsg({required this.text, required this.isUser, this.isError = false, this.richResult});
}
