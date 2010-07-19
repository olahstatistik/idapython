#------------------------------------------------------------
# IDAPython - Python plugin for Interactive Disassembler Pro
#
# Copyright (c) 2004-2009 Gergely Erdelyi <dyce@d-dome.net>
#
# All rights reserved.
#
# For detailed copyright information see the file COPYING in
# the root of the distribution archive.
#------------------------------------------------------------
"""
idautils.py - High level utility functions for IDA
"""
import idaapi
import idc
import types

def refs(ea, funcfirst, funcnext):
    """
    Generic reference collector - INTERNAL USE ONLY.
    """
    ref = funcfirst(ea)
    while ref != idaapi.BADADDR:
        yield ref
        ref = funcnext(ea, ref)


def CodeRefsTo(ea, flow):
    """
    Get a list of code references to 'ea'

    @param ea:   Target address
    @param flow: Follow normal code flow or not 
    @type  flow: Boolean (0/1, False/True)

    @return: list of references (may be empty list)

    Example::
    
        for ref in CodeRefsTo(ScreenEA(), 1):
            print ref
    """
    if flow == 1:
        return refs(ea, idaapi.get_first_cref_to, idaapi.get_next_cref_to)
    else:
        return refs(ea, idaapi.get_first_fcref_to, idaapi.get_next_fcref_to)


def CodeRefsFrom(ea, flow):
    """
    Get a list of code references from 'ea'

    @param ea:   Target address
    @param flow: Follow normal code flow or not 
    @type  flow: Boolean (0/1, False/True)

    @return: list of references (may be empty list)

    Example::
    
        for ref in CodeRefsFrom(ScreenEA(), 1):
            print ref
    """
    if flow == 1:
        return refs(ea, idaapi.get_first_cref_from, idaapi.get_next_cref_from)
    else:
        return refs(ea, idaapi.get_first_fcref_from, idaapi.get_next_fcref_from)


def DataRefsTo(ea):
    """
    Get a list of data references to 'ea'

    @param ea:   Target address

    @return: list of references (may be empty list)

    Example::
    
        for ref in DataRefsTo(ScreenEA(), 1):
            print ref
    """
    return refs(ea, idaapi.get_first_dref_to, idaapi.get_next_dref_to)


def DataRefsFrom(ea):
    """
    Get a list of data references from 'ea'

    @param ea:   Target address

    @return: list of references (may be empty list)

    Example::
    
        for ref in DataRefsFrom(ScreenEA(), 1):
            print ref
    """
    return refs(ea, idaapi.get_first_dref_from, idaapi.get_next_dref_from)


def XrefTypeName(typecode):
    """
    Convert cross-reference type codes to readable names

    @param typecode: cross-reference type code
    """
    ref_types = {
        0  : 'Data_Unknown',
        1  : 'Data_Offset',
        2  : 'Data_Write',
        3  : 'Data_Read',
        4  : 'Data_Text',
        5  : 'Data_Informational',
        16 : 'Code_Far_Call',
        17 : 'Code_Near_Call',
        18 : 'Code_Far_Jump',
        19 : 'Code_Near_Jump',
        20 : 'Code_User',
        21 : 'Ordinary_Flow'
        }
    assert typecode in ref_types, "unknown reference type %d" % typecode
    return ref_types[typecode]


def _copy_xref(xref):
    """ Make a private copy of the xref class to preserve its contents """
    class _xref(object):
        pass

    xr = _xref()
    for attr in [ 'frm', 'to', 'iscode', 'type', 'user' ]:
        setattr(xr, attr, getattr(xref, attr))
    return xr


def XrefsFrom(ea, flags=0):
    """ 
    Return all references from address 'ea'
    
    @param ea: Reference address
    @param flags: any of idaapi.XREF_* flags

    Example::
           for xref in XrefsFrom(here(), 0):
               print xref.type, XrefTypeName(xref.type), \
                         'from', hex(xref.frm), 'to', hex(xref.to)
    """
    xref = idaapi.xrefblk_t()
    if xref.first_from(ea, flags):
        yield _copy_xref(xref)
        while xref.next_from():
            yield _copy_xref(xref)


def XrefsTo(ea, flags=0):
    """
    Return all references to address 'ea'
    
    @param ea: Reference address
    @param flags: any of idaapi.XREF_* flags

    Example::
           for xref in XrefsTo(here(), 0):
               print xref.type, XrefTypeName(xref.type), \
                         'from', hex(xref.frm), 'to', hex(xref.to)
    """
    xref = idaapi.xrefblk_t()
    if xref.first_to(ea, flags):
        yield _copy_xref(xref)
        while xref.next_to():
            yield _copy_xref(xref)


def Threads():
    """Returns all thread IDs"""
    for i in xrange(0, idc.GetThreadQty()):
        yield idc.GetThreadId(i)


def Heads(start=None, end=None):
    """
    Get a list of heads (instructions or data)

    @param start: start address (default: inf.minEA)
    @param end:   end address (default: inf.maxEA)

    @return: list of heads between start and end
    """
    if not start: start = idaapi.cvar.inf.minEA
    if not end:   end = idaapi.cvar.inf.maxEA

    ea = start
    if not idc.isHead(idc.GetFlags(ea)):
        ea = idaapi.next_head(ea, end)
    while ea != idaapi.BADADDR:
        yield ea
        ea = idaapi.next_head(ea, end)


def Functions(start=None, end=None):
    """
    Get a list of functions

    @param start: start address (default: inf.minEA)
    @param end:   end address (default: inf.maxEA)

    @return: list of heads between start and end

    @note: The last function that starts before 'end' is included even
    if it extends beyond 'end'. Any function that has its chunks scattered
    in multiple segments will be reported multiple times, once in each segment
    as they are listed.
    """
    if not start: start = idaapi.cvar.inf.minEA
    if not end:   end = idaapi.cvar.inf.maxEA

    func = idaapi.get_func(start)
    if not func:
        func = idaapi.get_next_func(start)
    while func and func.startEA < end:
        yield func.startEA
        func = idaapi.get_next_func(func.startEA)


def Chunks(start):
    """
    Get a list of function chunks

    @param start: address of the function
       
    @return: list of funcion chunks (tuples of the form (start_ea, end_ea))
             belonging to the function
    """
    func_iter = idaapi.func_tail_iterator_t( idaapi.get_func( start ) )
    status = func_iter.main()
    while status:
        chunk = func_iter.chunk()
        yield (chunk.startEA, chunk.endEA)
        status = func_iter.next()


def Segments():
    """
    Get list of segments (sections) in the binary image

    @return: List of segment start addresses.
    """
    for n in xrange(idaapi.get_segm_qty()):
        seg = idaapi.getnseg(n)
        if seg:
            yield seg.startEA


def FuncItems(start):
    """
    Get a list of function items

    @param start: address of the function

    @return: ea of each item in the function
    """
    func = idaapi.get_func(start)
    if not func:
        return
    fii = idaapi.func_item_iterator_t()
    ok = fii.set(func)
    while ok:
        yield fii.current()
        ok = fii.next_code()


def DecodeInstruction(ea):
    """
    Decodes an instruction and returns an insn_t like class
    
    @param ea: address to decode

    @return: None or an insn_t like structure
    """
    inslen = idaapi.decode_insn(ea)
    if inslen == 0:
        return None
    insn = idaapi.get_current_instruction()
    if not insn:
        return None

    class _insn(object):
        def __getitem__(self, index):
            if index > len(self.Operands):
                raise StopIteration
            return self.Operands[index]

    class _op(_reg_dtyp_t):
        def __init__(self, op):
            _copy_obj(op, self)
            _reg_dtyp_t.__init__(self, op.reg, op.dtyp)
        def is_reg(self, r):
            """Checks if the operand is the given processor register"""
            return self.type == idaapi.o_reg and self == r
        def has_reg(self, r):
            """Checks if the operand accesses the given processor register"""
            return self.reg == r.reg
    r = _copy_obj(insn, _insn())
    r.Operands = [] # to hold the operands
    for n in xrange(0, idaapi.UA_MAXOP):
        t = idaapi.get_instruction_operand(insn, n)
        if t.type == idaapi.o_void:
            break
        r.Operands.append(_op(t))
    return r


def GetDataList(ea, count, itemsize=1):
    """
    Get data list - INTERNAL USE ONLY
    """
    if itemsize == 1:
        getdata = idaapi.get_byte
    elif itemsize == 2:
        getdata = idaapi.get_word
    elif itemsize == 4:
        getdata = idaapi.get_long
    elif itemsize == 8:
        getdata = idaapi.get_qword
    else:
        raise ValueError, "Invalid data size! Must be 1, 2, 4 or 8"

    endea = ea + itemsize * count
    curea = ea
    while curea < endea:
        yield getdata(curea)
        curea += itemsize


def PutDataList(ea, datalist, itemsize=1):
    """
    Put data list - INTERNAL USE ONLY
    """
    putdata = None

    if itemsize == 1:
        putdata = idaapi.patch_byte
    if itemsize == 2:
        putdata = idaapi.patch_word
    if itemsize == 4:
        putdata = idaapi.patch_long

    assert putdata, "Invalid data size! Must be 1, 2 or 4"

    for val in datalist:
        putdata(ea, val)
        ea = ea + itemsize


def MapDataList(ea, length, func, wordsize=1):
    """
    Map through a list of data words in the database

    @param ea:       start address
    @param length:   number of words to map
    @param func:     mapping function
    @param wordsize: size of words to map [default: 1 byte]

    @return: None
    """
    PutDataList(ea, map(func, GetDataList(ea, length, wordsize)), wordsize)


def GetInputFileMD5():
    """
    Return the MD5 hash of the input binary file

    @return: MD5 string or None on error
    """
    return idc.GetInputMD5()


class Strings(object):
    """
    Returns the string list.
	
	Example:
        s = Strings()

        for i in s:
            print "%x: len=%d type=%d -> '%s'" % (i.ea, i.length, i.type, str(i))

    """
    class StringItem(object):
        """
        Class representing each string item.
        The attributes are:
        ea - string ea
        type - string type (ASCSTR_xxxxx)
        str() - returns the actual string
        """
        def __init__(self, si):
            self.ea     = si.ea
            self.type   = si.type
            self.length = si.length
        def __str__(self):
            return idc.GetString(self.ea, self.length, self.type)

    STR_C       = 0x0001 # C-style ASCII string
    STR_PASCAL  = 0x0002 # Pascal-style ASCII string (length byte)
    STR_LEN2    = 0x0004 # Pascal-style, length is 2 bytes
    STR_UNICODE = 0x0008 # Unicode string
    STR_LEN4    = 0x0010 # Pascal-style, length is 4 bytes
    STR_ULEN2   = 0x0020 # Pascal-style Unicode, length is 2 bytes
    STR_ULEN4   = 0x0040 # Pascal-style Unicode, length is 4 bytes

    def clear_cache(self):
        """Clears the strings list cache"""
        self.refresh(0, 0) # when ea1=ea2 the kernel will clear the cache
    
    def __init__(self, default_setup=True):
        if default_setup:
            self.setup()
        self._si  = idaapi.string_info_t()
        self.size = 0

    def refresh(self, ea1=None, ea2=None):
        """Refreshes the strings list"""
        if not ea1: ea1 = idaapi.cvar.inf.minEA
        if not ea2: ea2 = idaapi.cvar.inf.maxEA
        idaapi.refresh_strlist(ea1, ea2)
        self.size = idaapi.get_strlist_qty()

    def setup(self, strtypes=STR_C, minlen=5, only_7bit=True, ignore_instructions=False,
              ea1=None, ea2=None, display_only_existing_strings=False):
        if not ea1: ea1 = idaapi.cvar.inf.minEA
        if not ea2: ea2 = idaapi.cvar.inf.maxEA
        t = idaapi.strwinsetup_t()
        t.strtypes = strtypes
        t.minlen = minlen
        t.only_7bit = only_7bit
        t.ea1 = ea1
        t.ea2 = ea2
        t.display_only_existing_strings = display_only_existing_strings
        idaapi.set_strlist_options(t)
        # automatically refreshes
        self.refresh()

    def __getitem__(self, index):
        """Returns string items"""
        if index >= self.size:
            raise StopIteration
        if idaapi.get_strlist_item(index, self._si):
            return Strings.StringItem(self._si)
        return None


def _Assemble(ea, line):
    """
    Please refer to Assemble() - INTERNAL USE ONLY
    """
    if type(line) == types.StringType:
        lines = [line]
    else:
        lines = line
    ret = []
    for line in lines:
        seg = idaapi.getseg(ea)
        if not seg:
            return (False, "No segment at ea")
        ip  = ea - (idaapi.ask_selector(seg.sel) << 4)
        buf = idaapi.AssembleLine(ea, seg.sel, ip, seg.bitness, line)
        if not buf:
            return (False, "Assembler failed: " + line)
        ea += len(buf)
        ret.append(buf)
    
    if len(ret) == 1:
        ret = ret[0]
    return (True, ret)


def Assemble(ea, line):
    """
    Assembles one or more lines (does not display an message dialogs)
    If line is a list then this function will attempt to assemble all the lines
    This function will turn on batch mode temporarily so that no messages are displayed on the screen

    @param ea:       start address
    @return: (False, "Error message") or (True, asm_buf) or (True, [asm_buf1, asm_buf2, asm_buf3])
    """
    old_batch = idc.Batch(1)
    ret = _Assemble(ea, line)
    idc.Batch(old_batch)
    return ret

def _copy_obj(src, dest):
    """
    Copy non private/non callable attributes from a class instance to another
    @param src: Source class to copy from
    @param dest: If it is a string then it designates the new class type that will be created and copied to.
                 Otherwise dest should be an instance of another class
    @return: A new instance or "dest"
    """
    if type(dest) == types.StringType:
        dest = new.classobj(dest, (), {})
    for x in dir(src):
        if x.startswith("__") and x.endswith("__"):
            continue
        t = getattr(src, x)
        if callable(t):
            continue
        setattr(dest, x, t)
    return dest

class _reg_dtyp_t(object):
    """
    INTERNAL
    This class describes a register's number and dtyp.
    The equal operator is overloaded so that two instances can be tested for equality
    """
    def __init__(self, reg, dtyp):
        self.reg  = reg
        self.dtyp = dtyp

    def __eq__(self, other):
        return (self.reg == other.reg) and (self.dtyp == other.dtyp)

class _procregs(object):
    """Utility class allowing the users to identify registers in a decoded instruction"""
    def __getattr__(self, attr):
        ri = idaapi.reg_info_t()
        if not idaapi.parse_reg_name(attr, ri):
            raise AttributeError()
        r = _reg_dtyp_t(ri.reg, ord(idaapi.get_dtyp_by_size(ri.size)))
        self.__dict__[attr] = r
        return r

    def __setattr__(self, attr, value):
        raise AttributeError(attr)

class _cpu(object):
    "Simple wrapper around GetRegValue/SetRegValue"
    def __getattr__(self, name):
        #print "cpu.get(%s)"%name
        return idc.GetRegValue(name)

    def __setattr__(self, name, value):
        #print "cpu.set(%s)"%name
        return idc.SetRegValue(value, name)

cpu = _cpu()
procregs = _procregs()