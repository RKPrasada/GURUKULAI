import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';
import '../utils/helpers.dart';

class MockScreen extends StatefulWidget {
  const MockScreen({super.key});

  @override
  State<MockScreen> createState() => _MockScreenState();
}

class _MockScreenState extends State<MockScreen> {
  String _selectedExam = '';
  Map<String, dynamic>? _paper;
  Map<String, dynamic>? _session;
  Map<String, dynamic>? _result;

  bool _loading = false;
  String? _error;

  // In-test state
  late List<int> _answers;
  late List<bool> _flagged;
  int _secondsLeft = 0;
  Timer? _timer;
  int _currentQ = 0;
  int _sectionIdx = 0;
  bool _submitted = false;

  @override
  void initState() {
    super.initState();
    final student = context.read<AuthProvider>().student!;
    _selectedExam = student.examTarget;
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  List<Map<String, dynamic>> get _sections =>
      (_paper?['sections'] as List?)?.cast<Map<String, dynamic>>() ?? [];

  List<Map<String, dynamic>> get _allQuestions {
    final qs = <Map<String, dynamic>>[];
    for (final s in _sections) {
      qs.addAll((s['questions'] as List?)?.cast<Map<String, dynamic>>() ?? []);
    }
    return qs;
  }

  // Global index range for current section
  int get _sectionStart {
    int idx = 0;
    for (int i = 0; i < _sectionIdx; i++) {
      idx += (_sections[i]['questions'] as List?)?.length ?? 0;
    }
    return idx;
  }

  int get _sectionEnd => _sectionStart +
      ((_sections.isNotEmpty ? (_sections[_sectionIdx]['questions'] as List?)?.length : null) ?? 0);

  Future<void> _loadStatus() async {
    setState(() { _loading = true; _error = null; });
    try {
      final status = await ApiService().getMockStatus(_selectedExam);
      final activeId = status['active_session_id'] as String?;
      if (activeId != null) {
        await _resumeSession(activeId);
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _startTest() async {
    setState(() { _loading = true; _error = null; });
    try {
      final data = await ApiService().startMockSession(_selectedExam);
      final sessionId = data['session_id'] as String;
      final paper = data['paper'] as Map<String, dynamic>? ?? await ApiService().getMockPaper(_selectedExam);
      _initSession(data, paper);
    } catch (e) {
      setState(() => _error = e.toString().replaceAll('ApiException(404): ', ''));
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _resumeSession(String sessionId) async {
    final data = await ApiService().getMockSession(sessionId);
    final paper = data['paper'] as Map<String, dynamic>?;
    if (paper == null) return;
    _initSession(data, paper, resume: true);
  }

  void _initSession(Map<String, dynamic> data, Map<String, dynamic> paper, {bool resume = false}) {
    _paper = paper;
    _session = data;
    final totalQ = _allQuestions.length;
    if (resume) {
      final savedAnswers = (data['answers'] as List?)?.cast<int>() ?? List.filled(totalQ, -1);
      final savedFlagged = (data['flagged'] as List?)?.cast<int>() ?? [];
      _answers = List.generate(totalQ, (i) => i < savedAnswers.length ? savedAnswers[i] : -1);
      _flagged = List.generate(totalQ, (i) => savedFlagged.contains(i));
    } else {
      _answers = List.filled(totalQ, -1);
      _flagged = List.filled(totalQ, false);
    }
    _secondsLeft = (data['seconds_remaining'] as num?)?.toInt() ??
        ((paper['duration_minutes'] as num?)?.toInt() ?? 90) * 60;
    _currentQ = 0;
    _sectionIdx = 0;
    _submitted = false;
    _startTimer();
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_secondsLeft <= 0) {
        _timer?.cancel();
        _autoSubmit();
      } else {
        setState(() => _secondsLeft--);
        if (_secondsLeft % 30 == 0) _autosave();
      }
    });
    setState(() {});
  }

  Future<void> _autosave() async {
    if (_session == null) return;
    final sessionId = _session!['session_id'] as String;
    final flaggedIdx = <int>[];
    for (int i = 0; i < _flagged.length; i++) {
      if (_flagged[i]) flaggedIdx.add(i);
    }
    try {
      await ApiService().autosaveMock(sessionId, _answers, flaggedIdx);
    } catch (_) {}
  }

  Future<void> _autoSubmit() async {
    await _autosave();
    await _submitTest();
  }

  Future<void> _submitTest() async {
    if (_session == null || _submitted) return;
    final sessionId = _session!['session_id'] as String;
    setState(() { _loading = true; _submitted = true; });
    _timer?.cancel();
    final flaggedIdx = <int>[];
    for (int i = 0; i < _flagged.length; i++) {
      if (_flagged[i]) flaggedIdx.add(i);
    }
    try {
      final result = await ApiService().submitMock(sessionId, _answers, flaggedIdx);
      setState(() => _result = result);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  void _reset() {
    _timer?.cancel();
    setState(() {
      _paper = null;
      _session = null;
      _result = null;
      _error = null;
      _submitted = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_result != null) return _ResultView(result: _result!, onRetry: _reset);
    if (_paper != null) return _TestView(this);
    return _LandingView(this);
  }
}

// ── Landing ──────────────────────────────────────────────────────────────────

class _LandingView extends StatelessWidget {
  final _MockScreenState s;
  const _LandingView(this.s);

  @override
  Widget build(BuildContext context) {
    final lang = context.watch<AuthProvider>().student?.preferredLanguage ?? 'en';
    return Scaffold(
      appBar: AppBar(title: Text(lang == 'hi' ? 'मॉक टेस्ट' : 'Mock Test')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('🧪', style: TextStyle(fontSize: 40)),
                  const SizedBox(height: 12),
                  Text(lang == 'hi' ? 'साप्ताहिक मॉक टेस्ट' : 'Weekly Mock Test',
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 4),
                  Text(lang == 'hi'
                      ? 'हर शनिवार एक नया पेपर उपलब्ध होता है'
                      : 'A new paper is available every Saturday',
                      style: TextStyle(color: Colors.grey.shade600)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text('Select Exam', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            value: AppConstants.examKeys.contains(s._selectedExam) ? s._selectedExam : AppConstants.examKeys.first,
            decoration: const InputDecoration(prefixIcon: Icon(Icons.school_outlined)),
            items: List.generate(AppConstants.examKeys.length, (i) => DropdownMenuItem(
              value: AppConstants.examKeys[i],
              child: Text(AppConstants.supportedExams[i]),
            )),
            onChanged: (v) => s.setState(() => s._selectedExam = v!),
          ),
          if (s._error != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.orange.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.orange.shade200),
              ),
              child: Text('⚠️  ${s._error}',
                  style: TextStyle(color: Colors.orange.shade800, fontSize: 13)),
            ),
          ],
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: s._loading ? null : s._startTest,
              icon: s._loading
                  ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Icon(Icons.play_arrow),
              label: Text(lang == 'hi' ? 'टेस्ट शुरू करें' : 'Start Mock Test',
                  style: const TextStyle(fontSize: 16)),
            ),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: s._loading ? null : s._loadStatus,
            icon: const Icon(Icons.refresh),
            label: Text(lang == 'hi' ? 'स्थिति जांचें' : 'Check Status / Resume'),
          ),
          const SizedBox(height: 24),
          _MockInfoCard(lang: lang),
        ],
      ),
    );
  }
}

class _MockInfoCard extends StatelessWidget {
  final String lang;
  const _MockInfoCard({required this.lang});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: AppTheme.primary.withOpacity(0.05),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(lang == 'hi' ? 'ℹ️ जानकारी' : 'ℹ️ About Mock Tests',
                style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            for (final line in lang == 'hi' ? [
              '• परीक्षा पैटर्न के अनुसार प्रश्न',
              '• नकारात्मक अंकन लागू होता है',
              '• टाइमर स्वचालित रूप से जमा करता है',
              '• परिणाम Dabbu द्वारा विश्लेषण किए जाते हैं',
            ] : [
              '• Questions follow official exam pattern',
              '• Negative marking applies (1/3 for RRB)',
              '• Timer auto-submits when time ends',
              '• Results are analyzed by Dabbu AI',
            ])
              Text(line, style: const TextStyle(fontSize: 13, height: 1.6)),
          ],
        ),
      ),
    );
  }
}

// ── In-Test View ─────────────────────────────────────────────────────────────

class _TestView extends StatelessWidget {
  final _MockScreenState s;
  const _TestView(this.s);

  @override
  Widget build(BuildContext context) {
    final lang = context.watch<AuthProvider>().student?.preferredLanguage ?? 'en';
    final allQs = s._allQuestions;
    if (allQs.isEmpty) return const Scaffold(body: Center(child: CircularProgressIndicator()));

    final q = allQs[s._currentQ];
    final options = (q['options'] as List?)?.cast<String>() ?? [];
    final mins = s._secondsLeft ~/ 60;
    final secs = s._secondsLeft % 60;
    final timerColor = s._secondsLeft < 300 ? Colors.red : AppTheme.primary;

    return Scaffold(
      appBar: AppBar(
        title: Text('Q ${s._currentQ + 1} / ${allQs.length}'),
        actions: [
          // Timer
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            margin: const EdgeInsets.only(right: 8),
            decoration: BoxDecoration(
              color: timerColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              '⏱ ${mins.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}',
              style: TextStyle(color: timerColor, fontWeight: FontWeight.w700),
            ),
          ),
        ],
        bottom: s._sections.length > 1
            ? PreferredSize(
                preferredSize: const Size.fromHeight(40),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: List.generate(s._sections.length, (i) => TextButton(
                      onPressed: () => s.setState(() {
                        s._sectionIdx = i;
                        s._currentQ = s._sectionStart;
                      }),
                      child: Text(
                        s._sections[i]['name'] as String? ?? 'Section ${i + 1}',
                        style: TextStyle(
                          color: s._sectionIdx == i ? AppTheme.primary : Colors.grey,
                          fontWeight: s._sectionIdx == i ? FontWeight.w700 : FontWeight.normal,
                        ),
                      ),
                    )),
                  ),
                ),
              )
            : null,
      ),
      body: Column(
        children: [
          // Question
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Flag button
                Row(
                  children: [
                    const Spacer(),
                    TextButton.icon(
                      onPressed: () => s.setState(() => s._flagged[s._currentQ] = !s._flagged[s._currentQ]),
                      icon: Icon(s._flagged[s._currentQ] ? Icons.flag : Icons.flag_outlined,
                          color: s._flagged[s._currentQ] ? Colors.orange : Colors.grey),
                      label: Text(s._flagged[s._currentQ] ? 'Flagged' : 'Flag',
                          style: TextStyle(color: s._flagged[s._currentQ] ? Colors.orange : Colors.grey)),
                    ),
                  ],
                ),
                Text(
                  q['question_text_en'] as String? ?? q['question_text'] as String? ?? '',
                  style: const TextStyle(fontSize: 16, height: 1.5, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 16),
                ...List.generate(options.length, (i) => GestureDetector(
                  onTap: () => s.setState(() => s._answers[s._currentQ] = i),
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 10),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: s._answers[s._currentQ] == i
                          ? AppTheme.primary.withOpacity(0.12)
                          : Colors.grey.shade50,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: s._answers[s._currentQ] == i ? AppTheme.primary : Colors.grey.shade200,
                        width: s._answers[s._currentQ] == i ? 2 : 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 13,
                          backgroundColor: s._answers[s._currentQ] == i ? AppTheme.primary : Colors.grey.shade300,
                          child: Text(
                            String.fromCharCode(65 + i),
                            style: TextStyle(
                              color: s._answers[s._currentQ] == i ? Colors.white : Colors.grey.shade700,
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(child: Text(options[i], style: const TextStyle(fontSize: 14))),
                      ],
                    ),
                  ),
                )),
              ],
            ),
          ),

          // Navigator + controls
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8, offset: const Offset(0, -2))],
            ),
            child: Column(
              children: [
                // Mini question grid for section
                SizedBox(
                  height: 44,
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    itemCount: s._sectionEnd - s._sectionStart,
                    itemBuilder: (_, i) {
                      final gi = s._sectionStart + i;
                      final answered = s._answers[gi] != -1;
                      final flagged = s._flagged[gi];
                      final isCurrent = gi == s._currentQ;
                      return GestureDetector(
                        onTap: () => s.setState(() => s._currentQ = gi),
                        child: Container(
                          width: 32,
                          height: 32,
                          margin: const EdgeInsets.only(right: 4),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: isCurrent
                                ? AppTheme.primary
                                : flagged
                                    ? Colors.orange
                                    : answered
                                        ? Colors.green
                                        : Colors.grey.shade200,
                          ),
                          alignment: Alignment.center,
                          child: Text('${i + 1}',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: (isCurrent || answered || flagged) ? Colors.white : Colors.grey.shade600,
                              )),
                        ),
                      );
                    },
                  ),
                ),
                // Prev / Next / Submit
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
                  child: Row(
                    children: [
                      OutlinedButton(
                        onPressed: s._currentQ > 0 ? () => s.setState(() => s._currentQ--) : null,
                        child: const Text('← Prev'),
                      ),
                      const Spacer(),
                      if (s._currentQ < s._allQuestions.length - 1)
                        ElevatedButton(
                          onPressed: () => s.setState(() => s._currentQ++),
                          child: const Text('Next →'),
                        )
                      else
                        ElevatedButton(
                          onPressed: s._loading ? null : () => _confirmSubmit(context, lang),
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                          child: s._loading
                              ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                              : Text(lang == 'hi' ? 'जमा करें' : 'Submit'),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _confirmSubmit(BuildContext context, String lang) {
    final answered = s._answers.where((a) => a != -1).length;
    final total = s._allQuestions.length;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(lang == 'hi' ? 'टेस्ट जमा करें?' : 'Submit Test?'),
        content: Text(lang == 'hi'
            ? 'आपने $answered/$total प्रश्नों के उत्तर दिए हैं।'
            : 'You answered $answered of $total questions. Submit now?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () { Navigator.pop(ctx); s._submitTest(); },
            child: Text(lang == 'hi' ? 'जमा करें' : 'Submit'),
          ),
        ],
      ),
    );
  }
}

// ── Result View ──────────────────────────────────────────────────────────────

class _ResultView extends StatelessWidget {
  final Map<String, dynamic> result;
  final VoidCallback onRetry;
  const _ResultView({required this.result, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final lang = context.watch<AuthProvider>().student?.preferredLanguage ?? 'en';
    final score = (result['total_score'] as num?)?.toDouble() ?? 0;
    final maxScore = (result['max_score'] as num?)?.toDouble() ?? 100;
    final pct = maxScore > 0 ? (score / maxScore * 100) : 0;
    final correct = (result['correct'] as num?)?.toInt() ?? 0;
    final wrong = (result['wrong'] as num?)?.toInt() ?? 0;
    final skipped = (result['skipped'] as num?)?.toInt() ?? 0;
    final sections = (result['sections'] as List?)?.cast<Map<String, dynamic>>() ?? [];

    return Scaffold(
      appBar: AppBar(title: Text(lang == 'hi' ? 'परिणाम' : 'Results')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: _scoreColor(pct.toDouble()).withOpacity(0.1),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  Text(_scoreEmoji(pct.toDouble()), style: const TextStyle(fontSize: 48)),
                  const SizedBox(height: 8),
                  Text(
                    '${score.toStringAsFixed(1)} / ${maxScore.toStringAsFixed(0)}',
                    style: TextStyle(fontSize: 32, fontWeight: FontWeight.w800,
                        color: _scoreColor(pct.toDouble())),
                  ),
                  Text('${pct.toStringAsFixed(1)}%',
                      style: const TextStyle(fontSize: 18, color: Colors.grey)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _ResultStat(label: lang == 'hi' ? 'सही' : 'Correct', value: '$correct', color: Colors.green),
              const SizedBox(width: 8),
              _ResultStat(label: lang == 'hi' ? 'गलत' : 'Wrong', value: '$wrong', color: Colors.red),
              const SizedBox(width: 8),
              _ResultStat(label: lang == 'hi' ? 'छोड़े' : 'Skipped', value: '$skipped', color: Colors.grey),
            ],
          ),
          if (sections.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(lang == 'hi' ? '📊 अनुभागवार' : '📊 Section Breakdown',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 8),
            ...sections.map((sec) {
              final secScore = (sec['score'] as num?)?.toDouble() ?? 0;
              final secMax = (sec['max_score'] as num?)?.toDouble() ?? 1;
              final secPct = secMax > 0 ? secScore / secMax : 0;
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text(sec['name'] as String? ?? 'Section'),
                  subtitle: LinearProgressIndicator(
                    value: secPct.toDouble(),
                    color: _scoreColor(secPct * 100),
                    backgroundColor: Colors.grey.shade200,
                  ),
                  trailing: Text('${secScore.toStringAsFixed(1)}/${secMax.toStringAsFixed(0)}',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
              );
            }),
          ],
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.blue.shade50,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              lang == 'hi'
                  ? '🤖 Dabbu आपके परिणामों का विश्लेषण कर रहा है और कमज़ोर क्षेत्रों पर एक योजना तैयार करेगा।'
                  : '🤖 Dabbu is analyzing your results and will prepare a focused study plan for your weak areas.',
              style: const TextStyle(fontSize: 13, height: 1.5),
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: Text(lang == 'hi' ? 'फिर से टेस्ट दें' : 'Take Another Test'),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Color _scoreColor(double pct) {
    if (pct >= 70) return Colors.green;
    if (pct >= 40) return Colors.orange;
    return Colors.red;
  }

  String _scoreEmoji(double pct) {
    if (pct >= 80) return '🏆';
    if (pct >= 60) return '✅';
    if (pct >= 40) return '📚';
    return '💪';
  }
}

class _ResultStat extends StatelessWidget {
  final String label, value;
  final Color color;
  const _ResultStat({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Column(
            children: [
              Text(value, style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: color)),
              Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
            ],
          ),
        ),
      ),
    );
  }
}
