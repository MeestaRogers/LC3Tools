import sublime
import sublime_plugin
import threading
import subprocess
import re
keys = [
    {
        'AND': 'DR, SR, VALUE',
        'DESC': '''If bit [5] is 0, the second source operand is obtained from SR2. If bit [5] is 1, the
second source operand is obtained by sign-extending the imm5 field to 16 bits.
In either case, the second source operand and the contents of SRI are bit-wise
ANDed, and the result stored in DR. The condition codes are set, based on whether
the binary value produced, taken as a 2's complement integer, is negative, zero,
or positive.''',
        'EXMP': '''AND\tR3,R3,0'''
    },
    {
        'ADD': 'DR, SR, VALUE',
        'DESC': '''If bit [5] is 0, the second source operand is obtained from SR2. If bit [5] is 1, the
second source operand is obtained by sign-extending the imm5 field to 16 bits.
In both cases, the second source operand is added to the contents of SRI and the
result stored in DR. The condition codes are set, based on whether the result is
negative, zero, or positive.''',
        'EXMP': '''ADD\tR3,R2,4'''
    },
    {
        'BR': 'LABEL',
        'DESC': '''The condition codes specified by the state of bits [11:9] are tested. If bit [11] is
set, N is tested; if bit [11] is clear, N is not tested. If bit [10] is set, Z is tested, etc.
If any of the condition codes tested is set, the program branches to the location
specified by adding the sign-extended PCoffset9 field to the incremented PC.''',
        'EXMP': '''BR\tLABEL_NAME'''
    },
    {
        'JMP': 'BaseR',
        'DESC': '''The program unconditionally jumps to the location specified by the contents of
the base register. Bits [8:6] identify the base register.''',
        'EXMP': '''JMP\tR2'''
    },
    {
        'JSR': 'LABEL',
        'JSRR': 'BaseR',
        'DESC': '''First, the incremented PC is saved in a temporary location. Then the PC is loaded
with the address of the first instruction of the subroutine, causing an unconditional
jump to that address. The address of the subroutine is obtained from the base
register (if bit [11] is 0), or the address is computed by sign-extending bits [10:0]
and adding this value to the incremented PC (if bit [ 11] is 1). Finally, R7 is loaded
with the value stored in the temporary location. This is the linkage back to the
calling routine.''',
        'EXMP': '''<br>JSR\tLABEL_NAME<br>JSRR\tR3'''
    },
    {
        'LD': 'DR, LABEL',
        'DESC': '''An address is computed by sign-extending bits [8:0] to 16 bits and adding this
value to the incremented PC. The contents of memory at this address are loaded
into DR. The condition codes are set, based on whether the value loaded is
negative, zero, or positive.''',
        'EXMP': '''LD\tR5,VALUE'''
    },
    {
        'LDI': 'DR, LABEL',
        'DESC': '''An address is computed by sign-extending bits [8:0] to 16 bits and adding this
value to the incremented PC. What is stored in memory at this address is the
address of the data to be loaded into DR. The condition codes are set, based on
whether the value loaded is negative, zero, or positive.''',
        'EXMP': '''LDI\tR5,MY_LABEL'''
    },
    {
        'LDR': 'DR, SR, offset6',
        'DESC': '''An address is computed by sign-extending bits [5:0] to 16 bits and adding this
value to the contents of the register specified by bits [8:6]. The contents of memory
at this address are loaded into DR. The condition codes are set, based on whether
the value loaded is negative, zero, or positive.''',
        'EXMP': '''LDR\tR5,R2,#-5'''
    },
    {
        'LEA': 'DR, LABEL',
        'DESC': '''An address is computed by sign-extending bits [8:0] to 16 bits and adding this
value to the incremented PC. This address is loaded into DR.4" The condition
codes are set, based on whether the value loaded is negative, zero, or positive.''',
        'EXMP': '''LEA\tR5,MY_LABEL'''
    },
    {
        'NOT': 'DR, SR',
        'DESC': '''The bit-wise complement of the contents of SR is stored in DR. The condition
codes are set, based on whether the binary value produced, taken as a 2's
complement integer, is negative, zero, or positive.''',
        'EXMP': '''NOT\tR5,R3'''
    },
    {
        'RET': '',
        'DESC': '''The PC is loaded with the value in R7. This causes a return from a previous JSR
instruction.''',
        'EXMP': '''RET ; PC ← R7'''
    },
    {
        'RTI': '',
        'DESC': '''If the processor is running in Supervisor mode, the top two elements on the
Supervisor Stack are popped and loaded into PC, PSR. If the processor is running
in User mode, a privilege mode violation exception occurs.''',
        'EXMP': '''RTI ; PC,PSR ← top two values popped off stack.'''
    },
    {
        'ST': 'SR, LABEL',
        'DESC': '''The contents of the register specified by SR are stored in the memory location
whose address is computed by sign-extending bits [8:0] to 16 bits and adding this
value to the incremented PC.''',
        'EXMP': '''ST R5, MY_LABEL'''
    },
    {
        'STI': 'SR, LABEL',
        'DESC': '''The contents of the register specified by SR are stored in the memory location
whose address is obtained as follows: Bits [8:0] are sign-extended to 16 bits and
added to the incremented PC. What is in memory at this address is the address of
the location to which the data in SR is stored.''',
        'EXMP': '''STI R5, MY_LABEL'''
    },
    {
        'STR': 'SR, BaseR,offset6',
        'DESC': '''The contents of the register specified by SR are stored in the memory location
whose address is computed by sign-extending bits [5:0] to 16 bits and adding this
value to the contents of the register specified by bits [8:6].''',
        'EXMP': '''STR R4, R2, #5'''
    },
    {
        'TRAP': 'trapvector8',
        'DESC': '''First R7 is loaded with the incremented PC. (This enables a return to the instruction
physically following the TRAP instruction in the original program after the service
routine has completed execution.) Then the PC is loaded with the starting address
of the system call specified by trapvector8. The starting address is contained in
the memory location whose address is obtained by zero-extending trapvector8 to
16 bits.''',
        'EXMP': '''TRAP x23'''
    },
    {
        'GETC': '',
        'DESC': '''Read a single character from the keyboard. The character is not echoed onto the
console. Its ASCII code is copied into RO. The high eight bits of RO are cleared.''',
        'EXMP': '''<br>GETC<br>OUT'''
    },
    {
        'OUT': '',
        'DESC': '''Write a character in R0[7:0] to the console display.''',
        'EXMP': '''<br>GETC<br>OUT'''
    },
    {
        'PUTS': '',
        'DESC': '''Write a string of ASCII characters to the console display. The characters are contained
in consecutive memory locations, one character per memory location, starting with
the address specified in RO. Writing terminates with the occurrence of xOOOO in a
memory location.''',
        'EXMP': '''<br>LEA\tR0,MY_STRING<br>PUTS'''
    },
    {
        'IN': '',
        'DESC': '''Print a prompt on the screen and read a single character from the keyboard. The
character is echoed onto the console monitor, and its ASCII code is copied into RO.''',
        'EXMP': '''<br>IN<br>OUT'''
    },
    {
        'PUTSP': '',
        'DESC': '''Write a string of ASCII characters to the console. The characters are contained in
consecutive memory locations, two characters per memory location, starting with the
address specified in RO. The ASCII code contained in bits [7:0] of a memory location
is written to the console first. Then the ASCII code contained in bits [15:8] of that
memory location is written to the console. (A character string consisting of an odd
number of characters to be written will have xOO in bits [15:8J of the memory
location containing the last character to be written.) Writing terminates with the
occurrence of xOOOO in a memory location.''',
        'EXMP': '''<br>PUTSP'''
    },
    {
        'HALT': '',
        'DESC': '''Halt execution and print a message on the console.''',
        'EXMP': '''<br>; Some code<br>HALT'''
    },
]
def in_show_popup(self):
    is_asm = len(self.view.sel()) > 0 and self.view.score_selector(max(self.view.sel()[0].a,self.view.sel()[0].b), "source.asm") > 0
    is_ssraw = len(self.view.sel()) > 0 and self.view.score_selector(max(self.view.sel()[0].a,self.view.sel()[0].b), "source.ssraw") > 0
    if(is_asm or is_ssraw):
        index = -1
        key = str(self.view.substr(self.view.word(self.view.sel()[0])))
        key = re.sub('(n|z|p)','', key)
        i = 0
        for data in keys:
            if(not (data.get(key) == None)):
                index = i
                break
            i = i + 1
        if(not(index == -1)):
            template = '''
                <style>
                    .key{
                        color: red;
                        display: inline-block;
                    }
                    .snip{
                        color: purple;
                        display: inline-block;
                        padding-right:48px;
                        text-align:right
                    }
                    .body{
                        font-style: italic;
                    }
                </style>
                <div>
                    <h4><label class="key">%s</label>&nbsp;&nbsp;&nbsp;&nbsp;<label class="snip">%s</label></h4>
                    <p class="body">%s</p>
                    <span>Example: <code>%s</code></span>
                </div>
            '''
            template = format(template % (key, keys[index][key], keys[index]["DESC"], keys[index]["EXMP"]))
            if(self.view.is_popup_visible()):
                self.view.update_popup(template)
            else:
                self.view.show_popup(template, sublime.COOPERATE_WITH_AUTO_COMPLETE, max_width=480)
        else:
            self.view.hide_popup()
def sim():
    print("Should start simulating...")
    subprocess.call("lc3sim");
    subprocess.call("name", "data.obj")
    subprocess.call("name", "MinMaxArray.obj")

class Lc3ShowToolTip(sublime_plugin.ViewEventListener):
    def on_modified(self):
        in_show_popup(self)

class Lc3SimulateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        print("Called my macro")
        mythread = threading.Thread(target=sim)
        try:
            mythread.start()
            mythread.join()
        except Exception as e:
            raise e