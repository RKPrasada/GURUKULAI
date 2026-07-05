import 'dart:async';
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

  static const _generatePhrases = [
    'Analysing your weak areas…',
    'Building your weekly schedule…',
    'Calibrating difficulty for each topic…',
    'Finalising your year plan…',
  ];
  int _phraseIdx = 0;
  Timer? _phraseTimer;

  @override
  void initState() {
    super.initState();
    _loadPlans();
  }

  @override
  void dispose() {
    _phraseTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadPlans() async {
    setState(() { _loading = true; _error = null; });
    try {
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
    setState(() { _generating = true; _phraseIdx = 0; });
    _phraseTimer = Timer.periodic(const Duration(milliseconds: 1800), (_) {
      if (mounted) setState(() => _phraseIdx = (_phraseIdx + 1) % _generatePhrases.length);
    });
    try {
      final res = await ApiService().generateStudyPlan();
      _phraseTimer?.cancel();
      setState(() {
        _proposedPlan = res['plan'] as Map<String, dynamic>?;
        _generating = false;
      });
    } catch (e) {
      _phraseTimer?.cancel();
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

    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator(color: AppTheme.primary)));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Study Plan'),
        actions: [
          if (_activePlan != null || _proposedPlan != null)
            IconButton(icon: const Icon(Icons.refresh), onPressed: _loadPlans),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadPlans,
        child: _buildBody(diagnosticDone),
      ),
    );
  }

  Widget _buildBody(bool diagnosticDone) {
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 12),
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _loadPlans, child: const Text('Retry')),
          ]),
        ),
      );
    }

    if (!diagnosticDone) return _DiagnosticGate();

    if (_generating) return _GeneratingView(phrase: _generatePhrases[_phraseIdx]);

    if (_activePlan != null) return _ActivePlanView(plan: _activePlan!, onRefresh: _loadPlans);

    if (_proposedPlan != null) return _ProposedView(plan: _proposedPlan!, onRefresh: _loadPlans);

    return _GeneratePrompt(onGenerate: _generate);
  }
}

// ── Diagnostic gate ────────────────────────────────────────────────────────────

class _DiagnosticGate extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.assignment_outlined, size: 64, color: AppTheme.secondary),
          const SizedBox(height: 20),
          const Text('Complete the diagnostic first',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Text('Dabbu needs your diagnostic results to build a personalised plan.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey.shade600)),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            icon: const Icon(Icons.quiz_outlined),
            label: const Text('Go to Diagnostic'),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const DiagnosticScreen())),
          ),
        ]),
      ),
    );
  }
}

// ── Generating spinner ─────────────────────────────────────────────────────────

class _GeneratingView extends StatelessWidget {
  final String phrase;
  const _GeneratingView({required this.phrase});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const SizedBox(
            width: 48, height: 48,
            child: CircularProgressIndicator(strokeWidth: 3, color: AppTheme.primary),
          ),
          const SizedBox(height: 24),
          Text(phrase,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppTheme.primary)),
          const SizedBox(height: 8),
          Text('NAGA will review before it goes live.',
              style: TextStyle(color: Colors.grey.shade500, fontSize: 13)),
        ]),
      ),
    );
  }
}

// ── Generate prompt ────────────────────────────────────────────────────────────

class _GeneratePrompt extends StatelessWidget {
  final VoidCallback onGenerate;
  const _GeneratePrompt({required this.onGenerate});

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(24), children: [
      const SizedBox(height: 24),
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
      const Center(
        child: Text('Build your study plan',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
      ),
      const SizedBox(height: 8),
      Center(
        child: Text(
          'Dabbu creates a day-by-day schedule tailored to your weak areas.\nNAGA reviews it before it goes live.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey.shade600),
        ),
      ),
      const SizedBox(height: 32),
      // Feature chips
      ...[
        ('📅', 'Full year schedule', 'Week-by-week breakdown for every topic'),
        ('🎯', 'Weak area focus', 'Double weight on your lowest-scoring topics'),
        ('📊', 'Progress tracking', 'Mark blocks done, track completion rate'),
        ('👨‍🏫', 'NAGA reviewed', 'Your mentor checks the plan before you see it'),
      ].map((f) => Card(
        margin: const EdgeInsets.only(bottom: 10),
        child: ListTile(
          leading: Text(f.$1, style: const TextStyle(fontSize: 24)),
          title: Text(f.$2, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(f.$3, style: const TextStyle(fontSize: 12)),
        ),
      )),
      const SizedBox(height: 24),
      ElevatedButton.icon(
        icon: const Icon(Icons.auto_awesome),
        label: const Text('Generate My Study Plan'),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 14),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        onPressed: onGenerate,
      ),
    ]);
  }
}

// ── Proposed (awaiting NAGA) ───────────────────────────────────────────────────

class _ProposedView extends StatelessWidget {
  final Map<String, dynamic> plan;
  final VoidCallback onRefresh;
  const _ProposedView({required this.plan, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    final weeks = (plan['weeks'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    return ListView(padding: const EdgeInsets.all(16), children: [
      // Status banner
      Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.amber.shade50,
          border: Border.all(color: Colors.amber.shade200),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(children: [
          const SizedBox(
            width: 18, height: 18,
            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.amber),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Awaiting NAGA\'s review',
                style: TextStyle(fontWeight: FontWeight.w700, color: Colors.amber)),
            Text('Your plan is ready — NAGA will approve it shortly.',
                style: TextStyle(fontSize: 12, color: Colors.amber.shade700)),
          ])),
        ]),
      ),
      const SizedBox(height: 16),
      _PlanSummaryCard(plan: plan),
      const SizedBox(height: 16),
      Text('${weeks.length} weeks planned',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
      const SizedBox(height: 8),
      ...weeks.take(4).map((w) => _WeekTile(week: w, readOnly: true)),
      if (weeks.length > 4)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text('+ ${weeks.length - 4} more weeks',
              style: TextStyle(color: Colors.grey.shade500, fontSize: 13)),
        ),
    ]);
  }
}

// ── Active plan ────────────────────────────────────────────────────────────────

class _ActivePlanView extends StatefulWidget {
  final Map<String, dynamic> plan;
  final VoidCallback onRefresh;
  const _ActivePlanView({required this.plan, required this.onRefresh});

  @override
  State<_ActivePlanView> createState() => _ActivePlanViewState();
}

class _ActivePlanViewState extends State<_ActivePlanView> {
  int _selectedWeek = 1;

  @override
  Widget build(BuildContext context) {
    final weeks = (widget.plan['weeks'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    final selectedWeekData = weeks.firstWhere(
      (w) => w['week_number'] == _selectedWeek,
      orElse: () => weeks.isNotEmpty ? weeks.first : {},
    );

    return Column(children: [
      // Plan summary
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
        child: _PlanSummaryCard(plan: widget.plan),
      ),
      const SizedBox(height: 12),
      // Week selector
      SizedBox(
        height: 44,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          itemCount: weeks.length,
          itemBuilder: (_, i) {
            final w = weeks[i];
            final num = w['week_number'] as int;
            final active = num == _selectedWeek;
            return GestureDetector(
              onTap: () => setState(() => _selectedWeek = num),
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 4),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: active ? AppTheme.primary : Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  'Wk $num',
                  style: TextStyle(
                    color: active ? Colors.white : Colors.grey.shade700,
                    fontWeight: active ? FontWeight.w700 : FontWeight.normal,
                    fontSize: 13,
                  ),
                ),
              ),
            );
          },
        ),
      ),
      const SizedBox(height: 12),
      // Selected week detail
      Expanded(
        child: selectedWeekData.isEmpty
            ? const Center(child: Text('No week data'))
            : _WeekDetailView(week: selectedWeekData),
      ),
    ]);
  }
}

// ── Week detail ────────────────────────────────────────────────────────────────

class _WeekDetailView extends StatelessWidget {
  final Map<String, dynamic> week;
  const _WeekDetailView({required this.week});

  @override
  Widget build(BuildContext context) {
    final days = (week['days'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    return ListView(padding: const EdgeInsets.symmetric(horizontal: 16), children: [
      if ((week['theme'] as String? ?? '').isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(week['theme'] as String,
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
        ),
      ...days.map((day) => _DayCard(day: day)),
    ]);
  }
}

// ── Day card ───────────────────────────────────────────────────────────────────

class _DayCard extends StatelessWidget {
  final Map<String, dynamic> day;
  const _DayCard({required this.day});

  @override
  Widget build(BuildContext context) {
    final blocks = (day['blocks'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    final isRest = day['is_rest_day'] as bool? ?? false;
    final dayName = day['day_of_week'] as String? ?? '';
    final date = day['day_date'] as String? ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ExpansionTile(
        leading: _dayIcon(isRest, blocks),
        title: Text('$dayName${date.isNotEmpty ? ' · ${date.substring(5)}' : ''}',
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: isRest
            ? const Text('Rest day', style: TextStyle(color: Colors.grey))
            : Text('${blocks.length} block${blocks.length == 1 ? '' : 's'} · ${day['total_hours']?.toStringAsFixed(1) ?? '0'}h',
                style: const TextStyle(fontSize: 12)),
        children: blocks.map((b) => _BlockTile(block: b)).toList(),
      ),
    );
  }

  Widget _dayIcon(bool isRest, List blocks) {
    if (isRest) return const CircleAvatar(backgroundColor: Colors.grey, radius: 16, child: Icon(Icons.self_improvement, size: 16, color: Colors.white));
    final type = blocks.isNotEmpty ? (blocks.first['session_type'] as String? ?? 'study') : 'study';
    final colors = {'study': AppTheme.primary, 'practice': const Color(0xFF7C3AED), 'mock': Colors.red, 'revision': Colors.orange, 'rest': Colors.grey};
    final color = colors[type] ?? AppTheme.primary;
    return CircleAvatar(backgroundColor: color.withOpacity(0.15), radius: 16,
        child: Icon(Icons.calendar_today, size: 14, color: color));
  }
}

// ── Block tile ─────────────────────────────────────────────────────────────────

class _BlockTile extends StatelessWidget {
  final Map<String, dynamic> block;
  const _BlockTile({required this.block});

  static const _typeColors = {
    'study': AppTheme.primary,
    'practice': Color(0xFF7C3AED),
    'mock': Colors.red,
    'revision': Colors.orange,
    'rest': Colors.grey,
  };
  static const _typeIcons = {
    'study': Icons.menu_book_outlined,
    'practice': Icons.quiz_outlined,
    'mock': Icons.timer_outlined,
    'revision': Icons.replay_outlined,
    'rest': Icons.self_improvement,
  };

  @override
  Widget build(BuildContext context) {
    final type = block['session_type'] as String? ?? 'study';
    final color = _typeColors[type] ?? AppTheme.primary;
    final icon = _typeIcons[type] ?? Icons.school_outlined;
    final subject = block['subject'] as String? ?? '';
    final topic = block['topic'] as String? ?? '';
    final hours = block['duration_hours'] as int? ?? 2;
    final startHour = block['start_hour'] as int? ?? 8;
    final ampm = startHour >= 12 ? 'PM' : 'AM';
    final hour12 = startHour % 12 == 0 ? 12 : startHour % 12;

    return ListTile(
      dense: true,
      leading: Icon(icon, color: color, size: 18),
      title: Text(topic.isNotEmpty ? topic : subject,
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
      subtitle: Text('$subject · $hour12:00 $ampm · ${hours}h',
          style: const TextStyle(fontSize: 11)),
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(type, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
      ),
    );
  }
}

// ── Shared widgets ─────────────────────────────────────────────────────────────

class _PlanSummaryCard extends StatelessWidget {
  final Map<String, dynamic> plan;
  const _PlanSummaryCard({required this.plan});

  @override
  Widget build(BuildContext context) {
    final exam = (plan['exam_target'] as String? ?? '').toUpperCase().replaceAll('_', ' ');
    final months = plan['duration_months'] as int? ?? 6;
    final weeks = (plan['weeks'] as List<dynamic>? ?? []).length;
    final hours = plan['total_study_hours'] as num? ?? 0;
    final startDate = plan['start_date'] as String? ?? '';
    final endDate = plan['end_date'] as String? ?? '';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppTheme.primary, Color(0xFF7C3AED)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(exam, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 18)),
        const SizedBox(height: 4),
        Text('$months months · $weeks weeks · ${hours.toStringAsFixed(0)}h total',
            style: const TextStyle(color: Colors.white70, fontSize: 13)),
        if (startDate.isNotEmpty && endDate.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text('${startDate.substring(0, 10)} → ${endDate.substring(0, 10)}',
              style: const TextStyle(color: Colors.white60, fontSize: 12)),
        ],
      ]),
    );
  }
}

class _WeekTile extends StatelessWidget {
  final Map<String, dynamic> week;
  final bool readOnly;
  const _WeekTile({required this.week, this.readOnly = false});

  @override
  Widget build(BuildContext context) {
    final weekNum = week['week_number'] as int? ?? 0;
    final theme = week['theme'] as String? ?? '';
    final days = (week['days'] as List<dynamic>? ?? []).length;
    final hours = (week['total_hours'] as num?) ?? 0;
    return Card(
      margin: const EdgeInsets.only(bottom: 6),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppTheme.primary.withOpacity(0.1),
          child: Text('$weekNum', style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.w700)),
        ),
        title: Text(theme.isNotEmpty ? theme : 'Week $weekNum',
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text('$days days · ${hours.toStringAsFixed(1)}h',
            style: const TextStyle(fontSize: 12)),
        trailing: const Icon(Icons.chevron_right, size: 18),
      ),
    );
  }
}
