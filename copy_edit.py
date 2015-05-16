import sublime, sublime_plugin

selection_strings = []

line_endings = {'CR': '\r', 'Unix': '\n', 'Windows': '\r\n'}

#A note about copy_with_empty_selection
#----------------------------------------
#The way the built-in copy works is like this:
#all non-empty sels: copy them
#all empty sels: copy each whole line
#some non-empty sels, some empty: copy only the non-empty
#We're not going to do that, though. If they want to copy empty lines, we'll
#always copy empty lines. I don't understand the copying empty lines in the
#first place, but I would rather be internally consistent.

def print_status_message(verb, numregions=None):
	numregions = numregions or len(selection_strings)
	numchars = sum([len(s) for s in selection_strings])
	message = "{0} {1} character{2}".format(verb, numchars, 's' if numchars != 1 else '')
	if numregions > 1:
		message += " over {0} selection regions".format(numregions)
	sublime.status_message(message)

class CopyEditCommand(sublime_plugin.TextCommand):
	def copy(self, edit):
		#See copy_with_empty_selection note above.
		copy_with_empty_sel = self.view.settings().get("copy_with_empty_selection")
		
		new_sel_strings = []
		for s in self.view.sel():
			if len(s):
				new_sel_strings.append(self.view.substr(s))
			elif copy_with_empty_sel:
				new_sel_strings.append(self.view.substr(self.view.full_line(s)))
		
		if len(new_sel_strings) > 0:
			selection_strings[:] = [] #.clear() doesn't exist in 2.7
			selection_strings.extend(new_sel_strings)
			line_ending = line_endings[self.view.line_endings()]
			sublime.set_clipboard(line_ending.join(selection_strings))
			return True
		return False
	
	def run(self, edit, verb="Copied"):
		if self.copy(edit):
			print_status_message(verb)

class CutEditCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.run_command("copy_edit", {"verb":"Cut"})
		for s in reversed(self.view.sel()):
			if s.empty():
				# cut the whole line of empty sel as is default behavior
				self.view.erase(edit, self.view.full_line(s))
			else:
				self.view.erase(edit, s)

class PasteEditCommand(sublime_plugin.TextCommand):
	def run(self, edit, seperator=''):
		#check if clipboard is more up to date
		pasteboard = sublime.get_clipboard()
		from_clipboard = False
		if pasteboard != '\n'.join(selection_strings):
			selection_strings[:] = [] #.clear() doesn't exist in 2.7
			selection_strings.append(pasteboard)
			from_clipboard = True
		
		numstrings = len(selection_strings)
		numsels = len(self.view.sel())
		if numsels == 0:
			return
		
		if numstrings <= numsels and numsels % numstrings == 0:
			strs_per_sel = 1
		elif numsels < numstrings and numstrings % numsels == 0:
			strs_per_sel = int(numstrings / numsels)
		else:
			strs_per_sel = numstrings
		
		str_index = 0 
		new_sels = []
		for sel in self.view.sel():
			self.view.erase(edit, sel)
			insertion_point = sel.begin()
			strings_to_paste = selection_strings[str_index:str_index+strs_per_sel]
			for i, string in enumerate(strings_to_paste):
				separating = (i != len(strings_to_paste) - 1 and seperator)
				if separating:
					string += seperator
				self.view.insert(edit, insertion_point, string)
				insertion_point += len(string)
				if separating:
					region = sublime.Region(insertion_point - len(seperator))
				else:
					region = sublime.Region(insertion_point)
				new_sels.append(region)
			str_index = (str_index + strs_per_sel) % numstrings
		
		print_status_message("Pasted", len(self.view.sel()))
		
		self.view.sel().clear()
		for s in new_sels:
			self.view.sel().add(s)

class PasteEditSeperatorCommand(sublime_plugin.WindowCommand):
	def run(self):
		self.window.show_input_panel(
			  'Paste with seperator:', ', ', self.on_done, None, None, )

	def on_done(self, seperator):
		if self.window.active_view():
			pass
			self.window.active_view().run_command("paste_edit", {"seperator": seperator})


