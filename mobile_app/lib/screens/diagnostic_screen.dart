import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/session_provider.dart';
import '../theme/app_theme.dart';
import '../models/question_model.dart';

class DiagnosticScreen extends StatefulWidget {
  const DiagnosticScreen({super.key});

  @override
  State<DiagnosticScreen> createState() => _DiagnosticScreenState();
}

class _DiagnosticScreenState extends State<DiagnosticScreen> {
  int _page = 0;
  bool _started = false;
  bool _submitted = false;
  Map<String, dynamic>? _result;
  static const _perPage = 10;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _startTest());
  }

  Future<void> _startTest() async {
    final auth = context.read<AuthProvider>();
    final session = context.read<SessionProvider>();
    await session.startDiagnostic(auth.student!.studentId);
    setState(() => _started = true);
  }

  Future<void> _submit() async {
    final auth = context.read<AuthProvider>();
    final session = context.read<SessionProvider>();
    final result = await session.submitDiagnostic(auth.student!.studentId);
    if (result != null) {
      await auth.refreshStudent();
      setState(() { _result = result; _submitted = true; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionProvider>();
    final lang = context.read<AuthProvider>().student?.preferredLanguage ?? 'en';

    if (session.isLoading && !_started) {
      return Scaffold(
        appBar: AppBar(title: Text(lang == 'hi' ? 'डायग्नोस्टिक टेस्ट' : 'Diagnostic Test')),
        body: Center(child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(color: AppTheme.primary),
            const SizedBox(height: 24),
            Text(
              lang == 'hi' ? 'प्रश्न तैयार हो रहे हैं…' : 'Generating your diagnostic questions…',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(
              lang == 'hi' ? 'आपके एग्जाम के सिलेबस के अनुसार' : 'Tailored to your exam syllabus',
              style: TextStyle(color: Colors.grey.shade600),
            ),
          ],
        )),
      );
    }

    if (_submitted && _result != null) {
      return _ResultScreen(result: _result!, lang: lang);
    }

    final questions = session.questions;
    if (questions.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Diagnostic Test')),
        body: Center(child: Text(session.error ?? 'No questions loaded')),
      );
    }

    final start = _page * _perPage;
    final end = (start + _perPage).clamp(0, questions.length);
    final pageQuestions = questions.sublist(start, end);
    final isLastPage = end >= questions.length;

    return Scaffold(
      appBar: AppBar(
        title: Text(lang == 'hi' ? 'डायग्नोस्टिक टेस्ट' : 'Diagnostic Test'),
      ),
      body: Column(
        children: [
          LinearProgressIndicator(
            value: end / questions.length,
            backgroundColor: Colors.grey.shade200,
            valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.primary),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('${lang == 'hi' ? 'प्रश्न' : 'Questions'} ${start+1}–$end / ${questions.length}'),
                Text('${lang == 'hi' ? 'उत्तर दिए' : 'Answered'}: ${session.answers.where((a) => a != null).length}'),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: pageQuestions.length,
              itemBuilder: (context, i) {
                final q = pageQuestions[i];
                final globalIdx = start + i;
                return _QuestionCard(
                  question: q,
                  index: globalIdx,
                  lang: lang,
                  selectedAnswer: session.answers[globalIdx],
                  onAnswerSelected: (ans) => session.setAnswer(globalIdx, ans),
                );
              },
            ),
          ),
        ],
      ),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            if (_page > 0)
              Expanded(child: OutlinedButton(
                onPressed: () => setState(() => _page--),
                child: Text(lang == 'hi' ? '← पिछला' : '← Previous'),
              )),
            if (_page > 0) const SizedBox(width: 12),
            Expanded(child: ElevatedButton(
              onPressed: session.isLoading ? null : (isLastPage ? _submit : () => setState(() => _page++)),
              child: session.isLoading
                  ? Row(mainAxisSize: MainAxisSize.min, children: [
                      const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)),
                      const SizedBox(width: 8),
                      Text(lang == 'hi' ? 'विश्लेषण हो रहा है…' : 'Analysing your answers…'),
                    ])
                  : Text(isLastPage ? (lang == 'hi' ? '✅ सबमिट' : '✅ Submit') : (lang == 'hi' ? 'अगला →' : 'Next →')),
            )),
          ],
        ),
      ),
    );
  }
}

class _QuestionCard extends StatelessWidget {
  final Question question;
  final int index;
  final String lang;
  final int? selectedAnswer;
  final ValueChanged<int> onAnswerSelected;

  const _QuestionCard({
    required this.question, required this.index, required this.lang,
    required this.selectedAnswer, required this.onAnswerSelected,
  });

  @override
  Widget build(BuildContext context) {
    final text = question.textFor(lang);
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Q${index + 1}. $text', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
            const SizedBox(height: 12),
            ...List.generate(question.options.length, (i) {
              final selected = selectedAnswer == i;
              return InkWell(
                onTap: () => onAnswerSelected(i),
                borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                child: Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
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
                      Expanded(child: Text(question.options[i])),
                    ],
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _ResultScreen extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;
  const _ResultScreen({required this.result, required this.lang});

  @override
  Widget build(BuildContext context) {
    final score = ((result['score_pct'] as num? ?? 0) * 100).toStringAsFixed(0);
    final weakness = (result['weakness_map'] as List? ?? []).cast<Map<String, dynamic>>();
    return Scaffold(
      appBar: AppBar(title: Text(lang == 'hi' ? 'परिणाम' : 'Results')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: const Color(0xFFEDE7F6),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const Text('🎉', style: TextStyle(fontSize: 48)),
                  const SizedBox(height: 8),
                  Text('$score%', style: const TextStyle(fontSize: 48, fontWeight: FontWeight.w800, color: AppTheme.primary)),
                  Text(lang == 'hi' ? 'समग्र स्कोर' : 'Overall Score'),
                  const SizedBox(height: 8),
                  Text(result['summary'] as String? ?? ''),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(lang == 'hi' ? '📉 कमज़ोरी नक्शा' : '📉 Weakness Map',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
          const SizedBox(height: 8),
          ...weakness.map((w) {
            final pct = (w['score_pct'] as num).toDouble();
            return Card(
              child: ListTile(
                title: Text(w['topic'] as String),
                subtitle: Text(w['subject'] as String),
                trailing: SizedBox(
                  width: 80,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text('${(pct * 100).toStringAsFixed(0)}%',
                          style: TextStyle(fontWeight: FontWeight.bold,
                              color: pct < 0.4 ? Colors.red : pct < 0.6 ? Colors.orange : Colors.green)),
                      LinearProgressIndicator(value: pct, minHeight: 4,
                          color: pct < 0.4 ? Colors.red : pct < 0.6 ? Colors.orange : Colors.green),
                    ],
                  ),
                ),
              ),
            );
          }),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            child: Text(lang == 'hi' ? 'होम पर जाएं' : 'Go to Home'),
          ),
        ],
      ),
    );
  }
}
