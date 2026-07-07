import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'diagnostic_screen.dart';

class StudyPlanScreen extends StatefulWidget {
  const StudyPlanScreen({super.key});

  @override
  State<StudyPlanScreen> createState() => _StudyPlanScreenState();
}

class _StudyPlanScreenState extends State<StudyPlanScreen> {
  bool _loading = true;
  bool _generating = false;
  String? _error;
  Map<String, dynamic>? _activePlan;
  Map<String, dynamic>? _proposedPlan;

  @override
  void initState() {
    super.initState();
    _loadPlans();
  }

  Future<void> _loadPlans() async {
    setState(() { _loading = true; _error = null; });
    try {
      await context.read<AuthProvider>().refreshStudent();
      final results = await Future.wait([
        ApiService().getDabbuStudyPlan(),
        ApiService().getProposedStudyPlan(),
      ]);
      setState(() {
        _activePlan = results[0]['plan'] as Map<String, dynamic>?;
        _proposedPlan = results[1]['plan'] as Map<String, dynamic>?;
        _loading = false;
      });
    } catch (e) {
      setState(() { _error = 'Could not load study plan.'; _loading = false; });
    }
  }

  Future<void> _generate() async {
    setState(() { _generating = true; _error = null; });
    try {
      final res = await ApiService().generateStudyPlan();
      setState(() {
        _proposedPlan = res['plan'] as Map<String, dynamic>?;
        _generating = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Could not generate study plan. Please try again.';
        _generating = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final student = context.watch<AuthProvider>().student;
    final diagnosticDone = student?.diagnosticDone ?? false;
    final lang = student?.preferredLanguage ?? 'en';

    return Scaffold(
      appBar: AppBar(
        title: Text(lang == 'hi' ? 'आज की पढ़ाई' : "Today's Study Plan"),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadPlans),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadPlans,
        child: _buildBody(diagnosticDone, lang),
      ),
    );
  }

  Widget _buildBody(bool diagnosticDone, String lang) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 12),
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _loadPlans, child: Text(lang == 'hi' ? 'पुनः प्रयास' : 'Retry')),
          ]),
        ),
      );
    }

    if (!diagnosticDone) {
      return _DiagnosticGate(lang: lang);
    }

    if (_generating) {
      return Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const CircularProgressIndicator(color: AppTheme.primary),
          const SizedBox(height: 20),
          Text(
            lang == 'hi' ? 'Dabbu आपकी योजना बना रहा है…' : 'Dabbu is building your plan…',
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Text(
            lang == 'hi' ? 'NAGA अनुमोदन के बाद दिखेगा' : 'Will show after NAGA approves it',
            style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
          ),
        ]),
      );
    }

    // Show today's plan from active plan; proposed plan shows pending banner
    if (_proposedPlan != null && _activePlan == null) {
      return _TodayView(
        plan: _proposedPlan!,
        isPending: true,
        lang: lang,
        onRefresh: _loadPlans,
      );
    }

    if (_activePlan != null) {
      return _TodayView(
        plan: _activePlan!,
        isPending: false,
        lang: lang,
        onRefresh: _loadPlans,
      );
    }

    return _GeneratePrompt(onGenerate: _generate, lang: lang);
  }
}

// ── Today's plan view ──────────────────────────────────────────────────────────

class _TodayView extends StatelessWidget {
  final Map<String, dynamic> plan;
  final bool isPending;
  final String lang;
  final VoidCallback onRefresh;

  const _TodayView({
    required this.plan,
    required this.isPending,
    required this.lang,
    required this.onRefresh,
  });

  static const _typeColors = <String, Color>{
    'study':    Color(0xFF2563EB),
    'practice': Color(0xFFC026D3),
    'mock':     Color(0xFFDC2626),
    'revision': Color(0xFFF59E0B),
  };
  static const _typeBg = <String, Color>{
    'study':    Color(0xFFEFF6FF),
    'practice': Color(0xFFFDF4FF),
    'mock':     Color(0xFFFEF2F2),
    'revision': Color(0xFFFFFBEB),
  };
  static const _typeIcons = <String, IconData>{
    'study':    Icons.menu_book_outlined,
    'practice': Icons.quiz_outlined,
    'mock':     Icons.timer_outlined,
    'revision': Icons.replay_outlined,
  };

  Map<String, dynamic>? _findTodayData() {
    final today = DateTime.now().toIso8601String().substring(0, 10);
    final weeks = (plan['weeks'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    for (final week in weeks) {
      final days = (week['days'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
      for (final day in days) {
        if (day['day_date'] == today) return day;
      }
    }
    // Fallback: first non-rest day in first week
    for (final week in weeks) {
      final days = (week['days'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
      for (final day in days) {
        if (!(day['is_rest_day'] as bool? ?? false)) return day;
      }
    }
    return null;
  }

  String _fmt12h(int hour) {
    final h = hour % 12 == 0 ? 12 : hour % 12;
    final ampm = hour < 12 ? 'AM' : 'PM';
    return '$h:00 $ampm';
  }

  @override
  Widget build(BuildContext context) {
    final todayData = _findTodayData();
    final today = DateTime.now();
    final weekdays = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
    final dayName = weekdays[today.weekday - 1];
    final dateStr = '${today.day} ${_monthName(today.month)} ${today.year}';

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Pending banner
        if (isPending)
          Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.amber.shade50,
              border: Border.all(color: Colors.amber.shade200),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(children: [
              const Icon(Icons.hourglass_top, size: 18, color: Colors.amber),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  lang == 'hi' ? 'NAGA की समीक्षा के लिए प्रतीक्षारत' : 'Awaiting NAGA\'s review',
                  style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.amber),
                ),
              ),
            ]),
          ),

        // Date header
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppTheme.primary, Color(0xFF7C3AED)],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Row(children: [
            const Icon(Icons.today, color: Colors.white, size: 28),
            const SizedBox(width: 14),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(
                lang == 'hi' ? 'आज — $dayName' : 'Today — $dayName',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 18),
              ),
              Text(dateStr, style: const TextStyle(color: Colors.white70, fontSize: 13)),
            ]),
          ]),
        ),
        const SizedBox(height: 16),

        if (todayData == null) ...[
          Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.self_improvement, size: 56, color: Colors.grey),
              const SizedBox(height: 12),
              Text(
                lang == 'hi' ? 'आज कोई सत्र नहीं' : 'No sessions today',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              ),
              const SizedBox(height: 4),
              Text(
                lang == 'hi' ? 'आराम करें और कल के लिए तैयार हों!' : 'Rest up and come back tomorrow!',
                style: TextStyle(color: Colors.grey.shade500),
              ),
            ]),
          ),
        ] else if (todayData['is_rest_day'] as bool? ?? false) ...[
          Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Text('😌', style: TextStyle(fontSize: 52)),
              const SizedBox(height: 12),
              Text(
                lang == 'hi' ? 'आज विश्राम दिन है' : 'Rest Day Today',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
              ),
              const SizedBox(height: 4),
              Text(
                lang == 'hi' ? 'आपने यह अर्जित किया है! कल फिर मिलते हैं।' : "You've earned it! See you tomorrow.",
                style: TextStyle(color: Colors.grey.shade500),
              ),
            ]),
          ),
        ] else
          _buildDayBlocks(todayData, lang),
      ],
    );
  }

  Widget _buildDayBlocks(Map<String, dynamic> todayData, String lang) {
    final rawBlocks = (todayData['blocks'] as List<dynamic>? ?? [])
        .cast<Map<String, dynamic>>();
    final blocks = List<Map<String, dynamic>>.from(rawBlocks)
      ..sort((a, b) =>
          (a['start_hour'] as int? ?? 0).compareTo(b['start_hour'] as int? ?? 0));

    if (blocks.isEmpty) {
      return Text(
        lang == 'hi' ? 'आज कोई सत्र निर्धारित नहीं है।' : 'No sessions scheduled for today.',
        style: TextStyle(color: Colors.grey.shade500),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(children: [
          const Icon(Icons.schedule, size: 16, color: AppTheme.primary),
          const SizedBox(width: 6),
          Text(
            lang == 'hi'
                ? '${blocks.length} सत्र · ${(todayData['total_hours'] as num? ?? 0).toStringAsFixed(0)} घंटे'
                : '${blocks.length} sessions · ${(todayData['total_hours'] as num? ?? 0).toStringAsFixed(0)} hours',
            style: const TextStyle(fontWeight: FontWeight.w600, color: AppTheme.primary),
          ),
        ]),
        const SizedBox(height: 12),
        ...blocks.map((b) {
          final type = b['session_type'] as String? ?? 'study';
          final subject = b['subject'] as String? ?? '';
          final topic = b['topic'] as String? ?? '';
          final startHour = b['start_hour'] as int? ?? 0;
          final durHours = b['duration_hours'] as int? ?? 2;
          final color = _typeColors[type] ?? AppTheme.primary;
          final bg = _typeBg[type] ?? const Color(0xFFEFF6FF);
          final icon = _typeIcons[type] ?? Icons.school_outlined;

          return Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(12),
              border: Border(left: BorderSide(color: color, width: 4)),
            ),
            child: Row(children: [
              Icon(icon, color: color, size: 22),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  if (topic.isNotEmpty)
                    Text(topic, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                  if (subject.isNotEmpty)
                    Text(subject, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
                ]),
              ),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text(_fmt12h(startHour),
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color)),
                Text('${durHours}h', style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
              ]),
            ]),
          );
        }),
      ],
    );
  }

  String _monthName(int m) {
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return m >= 1 && m <= 12 ? months[m - 1] : '';
  }
}

// ── Diagnostic gate ────────────────────────────────────────────────────────────

class _DiagnosticGate extends StatelessWidget {
  final String lang;
  const _DiagnosticGate({required this.lang});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.assignment_outlined, size: 64, color: AppTheme.secondary),
          const SizedBox(height: 20),
          Text(
            lang == 'hi' ? 'पहले डायग्नोस्टिक टेस्ट दें' : 'Complete the Diagnostic First',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            lang == 'hi'
                ? 'Dabbu को आपकी योजना बनाने के लिए डायग्नोस्टिक परिणाम चाहिए।'
                : 'Dabbu needs your diagnostic results to build a personalised plan.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey.shade600),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            icon: const Icon(Icons.quiz_outlined),
            label: Text(lang == 'hi' ? 'डायग्नोस्टिक टेस्ट दें' : 'Take Diagnostic Test'),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const DiagnosticScreen())),
          ),
        ]),
      ),
    );
  }
}

// ── Generate prompt ────────────────────────────────────────────────────────────

class _GeneratePrompt extends StatelessWidget {
  final VoidCallback onGenerate;
  final String lang;
  const _GeneratePrompt({required this.onGenerate, required this.lang});

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(24), children: [
      const SizedBox(height: 32),
      Center(
        child: Container(
          width: 80, height: 80,
          decoration: BoxDecoration(
            color: AppTheme.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Icon(Icons.calendar_month_outlined, size: 40, color: AppTheme.primary),
        ),
      ),
      const SizedBox(height: 20),
      Center(
        child: Text(
          lang == 'hi' ? 'अपनी पढ़ाई योजना बनाएं' : 'Build Your Study Plan',
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
        ),
      ),
      const SizedBox(height: 8),
      Center(
        child: Text(
          lang == 'hi'
              ? 'Dabbu आपके कमज़ोर विषयों के आधार पर दैनिक योजना बनाएगा।\nNAGA इसे जांचेंगे।'
              : 'Dabbu creates a daily schedule tailored to your weak areas.\nNAGA reviews it before it goes live.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey.shade600),
        ),
      ),
      const SizedBox(height: 32),
      ElevatedButton.icon(
        icon: const Icon(Icons.auto_awesome),
        label: Text(
          lang == 'hi' ? 'मेरी पढ़ाई योजना बनाएं' : 'Generate My Study Plan',
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 14),
        ),
        onPressed: onGenerate,
      ),
    ]);
  }
}
