import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';

class TestScreen extends StatefulWidget {
  const TestScreen({super.key});

  @override
  State<TestScreen> createState() => _TestScreenState();
}

class _TestScreenState extends State<TestScreen> {
  bool _sessionStarted = false;
  int? _selectedOption;

  void _showAiChat(BuildContext context, String questionText, String lang) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusLarge)),
      ),
      builder: (_) => _AiChatSheet(questionText: questionText, lang: lang),
    );
  }

  Future<void> _startSession({String? topic}) async {
    final auth = context.read<AuthProvider>();
    final session = context.read<SessionProvider>();
    session.reset();
    await session.startAssessment(auth.student!.studentId, topic: topic);
    setState(() { _sessionStarted = true; _selectedOption = null; });
  }

  Future<void> _submitAnswer() async {
    if (_selectedOption == null) return;
    final auth = context.read<AuthProvider>();
    final session = context.read<SessionProvider>();
    await session.submitAssessmentAnswer(auth.student!.studentId, _selectedOption!);
    setState(() => _selectedOption = null);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionProvider>();
    final lang = context.watch<AuthProvider>().student?.preferredLanguage ?? 'en';

    if (!_sessionStarted) {
      return _TopicSelector(lang: lang, onStart: _startSession);
    }

    if (session.isLoading && session.questions.isEmpty) {
      return Scaffold(
        body: Center(child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(lang == 'hi' ? 'प्रश्न लोड हो रहे हैं...' : 'Loading questions...'),
          ],
        )),
      );
    }

    if (session.isComplete) {
      return _SessionComplete(session: session, lang: lang, onRetry: () => setState(() { _sessionStarted = false; session.reset(); }));
    }

    final q = session.currentQuestion;
    if (q == null) {
      return Scaffold(body: Center(child: Text(session.error ?? 'Error loading question')));
    }

    final lastResult = session.lastResult;

    return Scaffold(
      floatingActionButton: FloatingActionButton.small(
        onPressed: () => _showAiChat(context, q.textFor(lang), lang),
        backgroundColor: AppTheme.secondary,
        tooltip: lang == 'hi' ? 'AI से पूछें' : 'Ask AI',
        child: const Icon(Icons.psychology_outlined, color: Colors.white),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(child: LinearProgressIndicator(
                    value: session.questions.isEmpty ? 0 : session.currentIndex / 10,
                    minHeight: 8,
                    borderRadius: BorderRadius.circular(4),
                    color: AppTheme.primary,
                    backgroundColor: Colors.grey.shade200,
                  )),
                  const SizedBox(width: 12),
                  Text('${session.score}/${session.currentIndex}',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        _DifficultyBadge(difficulty: q.difficulty, lang: lang),
                        const SizedBox(width: 8),
                        Text(q.topic, style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      q.textFor(lang),
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600, height: 1.5),
                    ),
                    const SizedBox(height: 20),
                    if (lastResult == null) ...[
                      ...List.generate(q.options.length, (i) => _OptionTile(
                        label: q.options[i],
                        index: i,
                        selected: _selectedOption == i,
                        onTap: () => setState(() => _selectedOption = i),
                      )),
                    ] else ...[
                      ...List.generate(q.options.length, (i) {
                        final isCorrect = i == q.correctIndex;
                        final isSelected = i == lastResult['correct_index'];
                        Color? bg;
                        if (isCorrect) bg = const Color(0xFFE8F5E9);
                        if (isSelected && !isCorrect) bg = const Color(0xFFFFEBEE);
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: bg ?? Colors.grey.shade50,
                            border: Border.all(color: isCorrect ? Colors.green : Colors.grey.shade300),
                            borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                          ),
                          child: Row(
                            children: [
                              Icon(isCorrect ? Icons.check_circle : Icons.circle_outlined,
                                  color: isCorrect ? Colors.green : Colors.grey),
                              const SizedBox(width: 12),
                              Expanded(child: Text(q.options[i])),
                            ],
                          ),
                        );
                      }),
                      const SizedBox(height: 12),
                      Card(
                        color: const Color(0xFFF3E5F5),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(children: [
                                Icon(lastResult['correct'] == true ? Icons.check_circle : Icons.cancel,
                                    color: lastResult['correct'] == true ? Colors.green : Colors.red),
                                const SizedBox(width: 8),
                                Text(
                                  lastResult['correct'] == true
                                    ? (lang == 'hi' ? '✅ सही!' : '✅ Correct!')
                                    : (lang == 'hi' ? '❌ गलत!' : '❌ Wrong!'),
                                  style: const TextStyle(fontWeight: FontWeight.bold),
                                ),
                              ]),
                              const SizedBox(height: 8),
                              Text((lastResult['explanation_hi'] as String?) ?? lastResult['explanation_en'] as String? ?? ''),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: session.isLoading ? null : (lastResult != null ? session.clearLastResult : _submitAnswer),
                  child: session.isLoading
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : Text(lastResult != null
                          ? (lang == 'hi' ? 'अगला प्रश्न →' : 'Next Question →')
                          : (lang == 'hi' ? 'उत्तर सबमिट करें' : 'Submit Answer')),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DifficultyBadge extends StatelessWidget {
  final int difficulty;
  final String lang;
  const _DifficultyBadge({required this.difficulty, required this.lang});

  @override
  Widget build(BuildContext context) {
    final color = AppConstants.difficultyColors[difficulty] ?? Colors.grey;
    final label = (lang == 'hi' ? AppConstants.difficultyLabelsHi : AppConstants.difficultyLabels)[difficulty] ?? '';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(12), border: Border.all(color: color)),
      child: Text(label, style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 12)),
    );
  }
}

class _OptionTile extends StatelessWidget {
  final String label;
  final int index;
  final bool selected;
  final VoidCallback onTap;
  const _OptionTile({required this.label, required this.index, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: selected ? AppTheme.primary.withOpacity(0.1) : Colors.grey.shade50,
          border: Border.all(color: selected ? AppTheme.primary : Colors.grey.shade300),
          borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
        ),
        child: Row(
          children: [
            Icon(selected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                color: selected ? AppTheme.primary : Colors.grey),
            const SizedBox(width: 12),
            Expanded(child: Text(label)),
          ],
        ),
      ),
    );
  }
}

class _TopicSelector extends StatefulWidget {
  final String lang;
  final Future<void> Function({String? topic}) onStart;
  const _TopicSelector({required this.lang, required this.onStart});

  @override
  State<_TopicSelector> createState() => _TopicSelectorState();
}

class _TopicSelectorState extends State<_TopicSelector> {
  String? _topic;

  @override
  Widget build(BuildContext context) {
    final weaknesses = context.read<AuthProvider>().student?.weaknessMap ?? [];
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 32),
          Text(widget.lang == 'hi' ? '✏️ अभ्यास परीक्षा' : '✏️ Practice Test',
              style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: AppTheme.primary)),
          const SizedBox(height: 8),
          Text(widget.lang == 'hi' ? 'एडेप्टिव कठिनाई स्तर के साथ' : 'With adaptive difficulty',
              style: TextStyle(color: Colors.grey.shade600)),
          const SizedBox(height: 32),
          Text(widget.lang == 'hi' ? 'विषय चुनें (वैकल्पिक):' : 'Select topic (optional):',
              style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          Expanded(
            child: ListView(
              children: [
                Card(
                  child: RadioListTile<String?>(
                    value: null, groupValue: _topic,
                    title: Text(widget.lang == 'hi' ? '🎲 कमज़ोर विषयों से (सुझाई)' : '🎲 Random from weak areas (recommended)'),
                    onChanged: (v) => setState(() => _topic = v),
                    activeColor: AppTheme.primary,
                  ),
                ),
                ...weaknesses.take(5).map((w) => Card(
                  child: RadioListTile<String?>(
                    value: w.topic, groupValue: _topic,
                    title: Text(w.topic),
                    subtitle: Text('${w.subject} — ${(w.scorePct * 100).toStringAsFixed(0)}%'),
                    onChanged: (v) => setState(() => _topic = v),
                    activeColor: AppTheme.primary,
                  ),
                )),
              ],
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => widget.onStart(topic: _topic),
              child: Text(widget.lang == 'hi' ? '🚀 परीक्षा शुरू करें' : '🚀 Start Test'),
            ),
          ),
        ],
      ),
    );
  }
}

class _SessionComplete extends StatelessWidget {
  final SessionProvider session;
  final String lang;
  final VoidCallback onRetry;
  const _SessionComplete({required this.session, required this.lang, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final accuracy = session.currentIndex == 0 ? 0.0 : session.score / session.currentIndex * 100;
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('🎉', style: TextStyle(fontSize: 72)),
              const SizedBox(height: 16),
              Text(lang == 'hi' ? 'परीक्षा पूरी!' : 'Session Complete!',
                  style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700)),
              const SizedBox(height: 24),
              Text('${session.score}/${session.currentIndex}',
                  style: const TextStyle(fontSize: 56, fontWeight: FontWeight.w800, color: AppTheme.primary)),
              Text('${accuracy.toStringAsFixed(0)}% ${lang == 'hi' ? 'सटीकता' : 'Accuracy'}',
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 18)),
              const SizedBox(height: 32),
              ElevatedButton(onPressed: onRetry,
                  child: Text(lang == 'hi' ? '🔄 दोबारा खेलें' : '🔄 Try Again')),
            ],
          ),
        ),
      ),
    );
  }
}

// ── AI Chat Sheet ─────────────────────────────────────────────────────────────

class _ChatMsg {
  final bool isUser;
  final String text;
  final bool isGuardrail;
  const _ChatMsg({required this.isUser, required this.text, this.isGuardrail = false});
}

class _AiChatSheet extends StatefulWidget {
  final String questionText;
  final String lang;
  const _AiChatSheet({required this.questionText, required this.lang});

  @override
  State<_AiChatSheet> createState() => _AiChatSheetState();
}

class _AiChatSheetState extends State<_AiChatSheet> {
  final _ctrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final List<_ChatMsg> _msgs = [];
  bool _loading = false;

  @override
  void dispose() {
    _ctrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty || _loading) return;
    _ctrl.clear();
    setState(() {
      _msgs.add(_ChatMsg(isUser: true, text: text));
      _loading = true;
    });
    _scrollToBottom();
    try {
      final result = await ApiService().sendMessage('', text);
      final agent = result['agent'] as String?;
      final threat = result['threat'] as String?;
      final isGuardrail = agent == 'guardrail' || threat != null || result['quarantined'] == true;
      final reply = result['response'] as String? ??
          result['notes'] as String? ??
          result['message'] as String? ??
          (widget.lang == 'hi' ? 'कोई जवाब नहीं मिला।' : 'No response received.');
      setState(() => _msgs.add(_ChatMsg(isUser: false, text: reply, isGuardrail: isGuardrail)));
    } catch (e) {
      String msg;
      if (e is ApiException) {
        try {
          final body = jsonDecode(e.message) as Map<String, dynamic>;
          msg = body['detail'] as String? ?? e.message;
        } catch (_) {
          msg = e.message;
        }
      } else {
        msg = widget.lang == 'hi' ? 'जवाब नहीं मिला। फिर से कोशिश करें।' : 'Could not get a response. Please try again.';
      }
      setState(() => _msgs.add(_ChatMsg(isUser: false, text: msg)));
    } finally {
      setState(() => _loading = false);
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final lang = widget.lang;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SizedBox(
        height: MediaQuery.of(context).size.height * 0.65,
        child: Column(
          children: [
            Container(
              margin: const EdgeInsets.symmetric(vertical: 10),
              width: 40, height: 4,
              decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(2)),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Row(
                children: [
                  const Icon(Icons.psychology_outlined, color: AppTheme.secondary, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      lang == 'hi' ? 'इस प्रश्न के बारे में AI से पूछें' : 'Ask AI about this question',
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                    ),
                  ),
                  IconButton(icon: const Icon(Icons.close, size: 20), onPressed: () => Navigator.pop(context)),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: _msgs.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(
                          lang == 'hi'
                              ? 'इस प्रश्न के concept, formula या approach के बारे में कुछ भी पूछें।'
                              : 'Ask about the concept, formula, or approach for this question.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.grey.shade500, fontSize: 13),
                        ),
                      ),
                    )
                  : ListView.builder(
                      controller: _scrollCtrl,
                      padding: const EdgeInsets.all(12),
                      itemCount: _msgs.length,
                      itemBuilder: (_, i) {
                        final m = _msgs[i];
                        return Align(
                          alignment: m.isUser ? Alignment.centerRight : Alignment.centerLeft,
                          child: Container(
                            constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            decoration: BoxDecoration(
                              color: m.isUser
                                  ? AppTheme.primary
                                  : m.isGuardrail
                                      ? Colors.amber.shade50
                                      : Colors.grey.shade100,
                              borderRadius: BorderRadius.only(
                                topLeft: const Radius.circular(14),
                                topRight: const Radius.circular(14),
                                bottomLeft: Radius.circular(m.isUser ? 14 : 2),
                                bottomRight: Radius.circular(m.isUser ? 2 : 14),
                              ),
                              border: m.isGuardrail
                                  ? Border.all(color: Colors.amber.shade300)
                                  : null,
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (m.isGuardrail)
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 4),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.shield_outlined, size: 12, color: Colors.amber.shade700),
                                        const SizedBox(width: 4),
                                        Text('Guardrail', style: TextStyle(fontSize: 10, color: Colors.amber.shade700, fontWeight: FontWeight.bold)),
                                      ],
                                    ),
                                  ),
                                Text(
                                  m.text,
                                  style: TextStyle(
                                    color: m.isUser ? Colors.white : m.isGuardrail ? Colors.amber.shade900 : Colors.black87,
                                    fontSize: 13,
                                    height: 1.4,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
            if (_loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 4),
                child: LinearProgressIndicator(minHeight: 2),
              ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _ctrl,
                      decoration: InputDecoration(
                        hintText: lang == 'hi' ? 'यहाँ लिखें...' : 'Ask about this question…',
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide(color: Colors.grey.shade300),
                        ),
                        isDense: true,
                      ),
                      onSubmitted: (_) => _send(),
                      textInputAction: TextInputAction.send,
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _loading ? null : _send,
                    icon: const Icon(Icons.send, size: 18),
                    style: IconButton.styleFrom(backgroundColor: AppTheme.primary),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
