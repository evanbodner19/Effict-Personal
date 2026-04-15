import 'package:flutter/material.dart';
import '../models/item.dart';
import '../models/category.dart';

class ItemForm extends StatefulWidget {
  final List<Category> categories;
  final Item? existingItem;
  final void Function(Map<String, dynamic> data) onSubmit;

  const ItemForm({
    super.key,
    required this.categories,
    this.existingItem,
    required this.onSubmit,
  });

  @override
  State<ItemForm> createState() => _ItemFormState();
}

class _ItemFormState extends State<ItemForm> {
  late final TextEditingController _titleController;
  late final TextEditingController _notesController;
  late final TextEditingController _cadenceController;
  late final TextEditingController _freqTargetController;
  late final TextEditingController _freqWindowController;
  String? _selectedCategoryId;
  DateTime? _dueDate;
  DateTime? _startDate;
  bool _isProject = false;

  @override
  void initState() {
    super.initState();
    final item = widget.existingItem;
    _titleController = TextEditingController(text: item?.title ?? '');
    _notesController = TextEditingController(text: item?.notes ?? '');
    _cadenceController =
        TextEditingController(text: item?.cadenceDays?.toString() ?? '');
    _freqTargetController =
        TextEditingController(text: item?.frequencyTarget?.toString() ?? '');
    _freqWindowController =
        TextEditingController(text: item?.frequencyWindowDays?.toString() ?? '');
    _selectedCategoryId = item?.categoryId ?? widget.categories.first.id;
    _dueDate = item?.dueDate != null ? DateTime.tryParse(item!.dueDate!) : null;
    _startDate =
        item?.startDate != null ? DateTime.tryParse(item!.startDate!) : null;
    _isProject = item?.isProject ?? false;
  }

  void _submit() {
    final data = <String, dynamic>{
      'title': _titleController.text.trim(),
      'category_id': _selectedCategoryId,
    };
    if (_notesController.text.trim().isNotEmpty) {
      data['notes'] = _notesController.text.trim();
    }
    if (_dueDate != null) {
      data['due_date'] = _dueDate!.toIso8601String().split('T')[0];
    }
    if (_startDate != null) {
      data['start_date'] = _startDate!.toIso8601String().split('T')[0];
    }
    if (_cadenceController.text.isNotEmpty) {
      data['cadence_days'] = int.tryParse(_cadenceController.text);
    }
    if (_freqTargetController.text.isNotEmpty) {
      data['frequency_target'] = int.tryParse(_freqTargetController.text);
    }
    if (_freqWindowController.text.isNotEmpty) {
      data['frequency_window_days'] = int.tryParse(_freqWindowController.text);
    }
    data['is_project'] = _isProject;
    widget.onSubmit(data);
  }

  Future<void> _pickDate(bool isDue) async {
    final date = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    if (date != null) {
      setState(() {
        if (isDue) {
          _dueDate = date;
        } else {
          _startDate = date;
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _titleController,
            decoration: const InputDecoration(labelText: 'Title'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _notesController,
            decoration: const InputDecoration(labelText: 'Notes'),
            maxLines: 3,
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _selectedCategoryId,
            decoration: const InputDecoration(labelText: 'Category'),
            items: widget.categories
                .map((c) =>
                    DropdownMenuItem(value: c.id, child: Text(c.title)))
                .toList(),
            onChanged: (v) => setState(() => _selectedCategoryId = v),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pickDate(false),
                  child: Text(_startDate != null
                      ? 'Start: ${_startDate!.toIso8601String().split('T')[0]}'
                      : 'Start Date'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pickDate(true),
                  child: Text(_dueDate != null
                      ? 'Due: ${_dueDate!.toIso8601String().split('T')[0]}'
                      : 'Due Date'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _cadenceController,
            decoration: const InputDecoration(labelText: 'Cadence (days)'),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _freqTargetController,
                  decoration:
                      const InputDecoration(labelText: 'Frequency target'),
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _freqWindowController,
                  decoration:
                      const InputDecoration(labelText: 'Window (days)'),
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            title: const Text('Is Project'),
            value: _isProject,
            onChanged: (v) => setState(() => _isProject = v),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _submit,
            child: Text(widget.existingItem != null ? 'Update' : 'Create'),
          ),
        ],
      ),
    );
  }
}
