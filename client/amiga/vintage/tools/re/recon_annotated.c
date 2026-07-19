/* ===== FUN_00100000 @ 00100000 (size 302) ===== */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00100000(int param_1)

{
  byte *pbVar1;
  int in_D0;
  int iVar2;
  ushort uVar4;
  uint uVar3;
  short sVar5;
  uint uVar6;
  int iVar7;
  int in_A0;
  undefined4 *puVar8;
  int iVar9;
  undefined **ppuVar10;
  undefined *puStack_40;
  undefined4 local_3c;
  undefined4 local_38;
  undefined4 uStack_34;
  
  iVar9 = AbsExecBase;
  DAT_0011d04c = &uStack_34;
  SysBase = AbsExecBase;
  DAT_0011d048 = 0;
  local_38 = 0x100028;
  iVar2 = (**(code **)(AbsExecBase + -0x126))();    /* = SysBase.FindTask() */
  DAT_0011d038 = *(undefined4 *)(iVar2 + 0x98);
  if (*(int *)(iVar2 + 0xac) == 0) {
    DAT_0011d004 = (undefined1 *)(*(int *)(iVar2 + 0x3a) + 0x80);
    local_38 = 0x1000b8;
    FUN_001001c4();
    local_38 = 0x1000bc;
    uVar3 = FUN_001001b2();
    iVar7 = DOSBase;
    DAT_0011d048 = uVar3;
    local_38 = uVar3;
    if (*(undefined4 **)(uVar3 + 0x24) != (undefined4 *)0x0) {
      DAT_0011d038 = **(undefined4 **)(uVar3 + 0x24);
      local_3c = 0x1000dc;
      (**(code **)(DOSBase + -0x7e))();    /* = DOSBase.CurrentDir() */
      iVar9 = iVar7;
    }
    if (*(int *)(uVar3 + 0x20) != 0) {
      local_3c = 0x1000ec;
      DAT_0011d050 = (**(code **)(iVar9 + -0x1e))();
      if (DAT_0011d050 != 0) {
        *(undefined4 *)(iVar2 + 0xa4) = *(undefined4 *)(DAT_0011d050 * 4 + 8);
      }
    }
    local_3c = DAT_0011d048;
    ppuVar10 = &puStack_40;
    puStack_40 = &DAT_0011d000;
    DAT_0011d054 = *(byte **)(*(int *)(DAT_0011d048 + 0x24) + 4);
  }
  else {
    DAT_0011d004 = &stack0x00000080 + -param_1;
    local_38 = 0x10004c;
    FUN_001001c4();
    pbVar1 = (byte *)(*(int *)(*(int *)(iVar2 + 0xac) * 4 + 0x10) * 4);
    DAT_0011d054 = pbVar1 + 1;
    uVar6 = (uint)*pbVar1;
    local_38 = local_38 & 0xffff0000;
    iVar9 = -(uVar6 + in_D0 + 2 & 0xfffffffe);
    uVar3 = in_D0 - 1;
    iVar2 = uVar6 + in_D0;
    do {
      iVar7 = iVar2;
      *(undefined1 *)((int)&local_38 + (short)iVar7 + iVar9 + 2) =
           *(undefined1 *)(in_A0 + (short)uVar3);
      uVar4 = (short)uVar3 - 1;
      uVar3 = (uint)uVar4;
      iVar2 = iVar7 + -1;
    } while (uVar4 != 0xffff);
    *(undefined1 *)((int)&local_38 + (short)(iVar7 + -1) + iVar9 + 2) = 0x20;
    uVar3 = iVar7 - 2;
    do {
      sVar5 = (short)uVar3;
      *(byte *)((int)&local_38 + sVar5 + iVar9 + 2) = DAT_0011d054[sVar5];
      uVar3 = (uint)(ushort)(sVar5 - 1U);
    } while ((ushort)(sVar5 - 1U) != 0xffff);
    ppuVar10 = (undefined **)((int)&local_3c + iVar9 + 2);
    *(int *)((int)&local_3c + iVar9 + 2) = (int)&local_38 + iVar9 + 2;
  }
  sVar5 = 0xc80;
  puVar8 = &IntuitionBase;
  while (sVar5 = sVar5 + -1, sVar5 != -1) {
    *puVar8 = 0;
    puVar8 = puVar8 + 1;
  }
  *(undefined4 *)((int)ppuVar10 + -4) = 0x10012a;
  thunk_FUN_0011c000();
  *(undefined4 *)((int)ppuVar10 + -4) = 0;
  if (DAT_0011d02c != (code *)0x0) {
    *(undefined4 *)((int)ppuVar10 + -8) = 0x10013e;
    (*DAT_0011d02c)();
  }
  *(undefined4 *)((int)ppuVar10 + -8) = 0x100142;
  FUN_0010041e();
  iVar9 = AbsExecBase;
  *(undefined4 *)((int)ppuVar10 + -8) = 0x10014e;
  (**(code **)(AbsExecBase + -0x19e))();    /* = SysBase.CloseLibrary() */
  if (DAT_001200dc != 0) {
    *(undefined4 *)((int)ppuVar10 + -8) = 0x10015c;
    (**(code **)(iVar9 + -0x19e))();
  }
  if (DAT_001200e0 != 0) {
    *(undefined4 *)((int)ppuVar10 + -8) = 0x10016a;
    (**(code **)(iVar9 + -0x19e))();
  }
  if (DAT_0011d058 != 0) {
    *(undefined4 *)((int)ppuVar10 + -8) = 0x100178;
    (**(code **)(iVar9 + -0x19e))();
  }
  if (DAT_0011d048 != 0) {
    if (DAT_0011d03c != 0) {
      *(undefined4 *)((int)ppuVar10 + -8) = 0x100188;
      (**(code **)(iVar9 + -0x24))();
    }
    if (DAT_0011d050 != 0) {
      *(undefined4 *)((int)ppuVar10 + -8) = 0x100192;
      (**(code **)(iVar9 + -0x24))();
    }
    iVar9 = AbsExecBase;
    *(undefined4 *)((int)ppuVar10 + -8) = 0x10019a;
    (**(code **)(AbsExecBase + -0x84))();    /* = SysBase.Forbid() */
    *(undefined4 *)((int)ppuVar10 + -8) = 0x1001a2;
    (**(code **)(iVar9 + -0x17a))();
  }
  return CONCAT44(*(undefined4 *)((int)ppuVar10 + -4),*DAT_0011d04c);
}



/* ===== FUN_0010012e @ 0010012e (size 128) ===== */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_0010012e(undefined4 param_1)

{
  int iVar1;
  
  if (DAT_0011d02c != (code *)0x0) {
    (*DAT_0011d02c)();
  }
  FUN_0010041e();
  iVar1 = AbsExecBase;
  (**(code **)(AbsExecBase + -0x19e))();    /* = SysBase.CloseLibrary() */
  if (DAT_001200dc != 0) {
    (**(code **)(iVar1 + -0x19e))();
  }
  if (DAT_001200e0 != 0) {
    (**(code **)(iVar1 + -0x19e))();
  }
  if (DAT_0011d058 != 0) {
    (**(code **)(iVar1 + -0x19e))();
  }
  if (DAT_0011d048 != 0) {
    if (DAT_0011d03c != 0) {
      (**(code **)(iVar1 + -0x24))();
    }
    if (DAT_0011d050 != 0) {
      (**(code **)(iVar1 + -0x24))();
    }
    iVar1 = AbsExecBase;
    (**(code **)(AbsExecBase + -0x84))();    /* = SysBase.Forbid() */
    (**(code **)(iVar1 + -0x17a))();
  }
  return CONCAT44(param_1,*DAT_0011d04c);
}



/* ===== FUN_001001b2 @ 001001b2 (size 18) ===== */

void FUN_001001b2(void)

{
  int unaff_A6;
  
  (**(code **)(unaff_A6 + -0x180))();
  (**(code **)(unaff_A6 + -0x174))();
  return;
}



/* ===== FUN_001001c4 @ 001001c4 (size 22) ===== */
/* strings: dos.library */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int FUN_001001c4(void)

{
  int iVar1;
  int unaff_A6;
  
  DOSBase = (**(code **)(unaff_A6 + -0x228))();
  if (DOSBase != 0) {
    return DOSBase;
  }
  if (DAT_0011d02c != (code *)0x0) {
    (*DAT_0011d02c)();
  }
  FUN_0010041e();
  iVar1 = AbsExecBase;
  (**(code **)(AbsExecBase + -0x19e))();    /* = SysBase.CloseLibrary() */
  if (DAT_001200dc != 0) {
    (**(code **)(iVar1 + -0x19e))();
  }
  if (DAT_001200e0 != 0) {
    (**(code **)(iVar1 + -0x19e))();
  }
  if (DAT_0011d058 != 0) {
    (**(code **)(iVar1 + -0x19e))();
  }
  if (DAT_0011d048 != 0) {
    if (DAT_0011d03c != 0) {
      (**(code **)(iVar1 + -0x24))();
    }
    if (DAT_0011d050 != 0) {
      (**(code **)(iVar1 + -0x24))();
    }
    iVar1 = AbsExecBase;
    (**(code **)(AbsExecBase + -0x84))();    /* = SysBase.Forbid() */
    (**(code **)(iVar1 + -0x17a))();
  }
  return 100;
}



/* ===== thunk_FUN_0011c000 @ 001001d8 (size 6) ===== */

void thunk_FUN_0011c000(char *param_1)

{
  char cVar1;
  int iVar2;
  
  while (DAT_001230cc < 0x20) {
    for (; ((cVar1 = *param_1, cVar1 == ' ' || (cVar1 == '\t')) || (cVar1 == '\n'));
        param_1 = param_1 + 1) {
    }
    if (*param_1 == '\0') break;
    iVar2 = DAT_001230cc * 4;
    DAT_001230cc = DAT_001230cc + 1;
    if (*param_1 == '\"') {
      param_1 = param_1 + 1;
      *(char **)(&DAT_001230d4 + iVar2) = param_1;
      for (; (*param_1 != '\0' && (*param_1 != '\"')); param_1 = param_1 + 1) {
      }
      if (*param_1 == '\0') {
        thunk_FUN_0010169c(1);
      }
      else {
        *param_1 = '\0';
        param_1 = param_1 + 1;
      }
    }
    else {
      *(char **)(&DAT_001230d4 + iVar2) = param_1;
      for (; ((*param_1 != '\0' && (cVar1 = *param_1, cVar1 != ' ')) &&
             ((cVar1 != '\t' && (cVar1 != '\n')))); param_1 = param_1 + 1) {
      }
      if (*param_1 == '\0') break;
      *param_1 = '\0';
      param_1 = param_1 + 1;
    }
  }
  DAT_001230d0 = DAT_0011d048;
  if (DAT_001230cc != 0) {
    DAT_001230d0 = &DAT_001230d4;
  }
  thunk_FUN_001029e6(DAT_001230cc,DAT_001230d0);
  thunk_FUN_0010169c(0);
  return;
}



/* ===== FUN_001001e0 @ 001001e0 (size 72) ===== */

undefined4 * FUN_001001e0(int param_1)

{
  undefined4 *puVar1;
  
  DAT_0011d018 = 0;
  if (((param_1 < 0) || (DAT_001200d4 <= param_1)) || ((&DAT_001231a8)[param_1 * 2] == 0)) {
    DAT_00120038 = 9;
    puVar1 = (undefined4 *)0x0;
  }
  else {
    puVar1 = &DAT_001231a8 + param_1 * 2;
  }
  return puVar1;
}



/* ===== FUN_00100240 @ 00100240 (size 90) ===== */

void FUN_00100240(undefined4 param_1)

{
  undefined **ppuVar1;
  
  for (ppuVar1 = &PTR_PTR_00120050; ppuVar1 != (undefined **)0x0; ppuVar1 = (undefined **)*ppuVar1)
  {
    if (((*(byte *)((int)ppuVar1 + 0x1b) & 4) == 0) && ((*(byte *)((int)ppuVar1 + 0x1b) & 2) != 0))
    {
      if ((int)ppuVar1[1] - (int)ppuVar1[4] != 0) {
        FUN_00100a60(ppuVar1[7],ppuVar1[4],(int)ppuVar1[1] - (int)ppuVar1[4]);
      }
    }
  }
  FUN_0010169c(param_1);
  return;
}



/* ===== FUN_001002a4 @ 001002a4 (size 34) ===== */

undefined4 FUN_001002a4(int param_1)

{
  undefined4 uVar1;
  
  if ((param_1 < 0x30) || (0x39 < param_1)) {
    uVar1 = 0;
  }
  else {
    uVar1 = 1;
  }
  return uVar1;
}



/* ===== FUN_001002c8 @ 001002c8 (size 72) ===== */

undefined4 FUN_001002c8(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  int iVar1;
  undefined4 uVar2;
  
  iVar1 = FUN_001001e0(param_1);
  if (iVar1 == 0) {
    uVar2 = 0xffffffff;
  }
  else {
    uVar2 = FUN_00101798(*(undefined4 *)(iVar1 + 4),param_2,param_3);
    if (DAT_0011d018 != 0) {
      uVar2 = 0xffffffff;
    }
  }
  return uVar2;
}



/* ===== FUN_0010041e @ 0010041e (size 66) ===== */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0010041e(void)

{
  undefined4 local_8;
  
  local_8 = DAT_00123190;
  while (local_8 != (undefined4 *)0x0) {
    local_8 = (undefined4 *)*local_8;
    (**(code **)(AbsExecBase + -0xd2))();    /* = SysBase.FreeMem() */
  }
  DAT_00123194 = 0;
  DAT_00123190 = (undefined4 *)0x0;
  return;
}



/* ===== FUN_0010060e @ 0010060e (size 48) ===== */

undefined4 FUN_0010060e(undefined1 *param_1,undefined4 param_2)

{
  DAT_001231a0 = 0;
  DAT_0012319c = param_1;
  FUN_00100f46(&LAB_001005f4,param_2,&stack0x0000000c);
  *DAT_0012319c = 0;
  return DAT_001231a0;
}



/* ===== FUN_001007bc @ 001007bc (size 156) ===== */

int FUN_001007bc(char *param_1,int *param_2)

{
  bool bVar1;
  int iVar2;
  int local_c;
  int local_8;
  
  local_8 = 0;
  local_c = 0;
  bVar1 = false;
  if (*param_1 == '-') {
    local_c = 1;
    bVar1 = true;
  }
  else if (*param_1 == '+') {
    local_c = 1;
  }
  while( true ) {
    iVar2 = FUN_001002a4(param_1[local_c]);
    if (iVar2 == 0) break;
    iVar2 = FUN_00101604();
    local_8 = (uint)(byte)param_1[local_c] + iVar2 + -0x30;
    local_c = local_c + 1;
  }
  if (bVar1) {
    local_8 = -local_8;
  }
  *param_2 = local_8;
  return local_c;
}



/* ===== FUN_00100a48 @ 00100a48 (size 22) ===== */

char FUN_00100a48(char param_1)

{
  if (('`' < param_1) && (param_1 < '{')) {
    param_1 = param_1 + -0x20;
  }
  return param_1;
}



/* ===== FUN_00100a60 @ 00100a60 (size 102) ===== */

undefined4 FUN_00100a60(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  int iVar1;
  undefined4 uVar2;
  
  iVar1 = FUN_001001e0(param_1);
  if (iVar1 == 0) {
    uVar2 = 0xffffffff;
  }
  else {
    if ((*(byte *)(iVar1 + 3) & 8) != 0) {
      FUN_001002c8(param_1,0,2);
    }
    uVar2 = FUN_00101740(*(undefined4 *)(iVar1 + 4),param_2,param_3);
    if (DAT_0011d018 != 0) {
      uVar2 = 0xffffffff;
    }
  }
  return uVar2;
}



/* ===== FUN_00100ad0 @ 00100ad0 (size 304) ===== */

undefined4 FUN_00100ad0(byte *param_1,int *param_2)

{
  undefined4 *puVar1;
  byte *pbVar2;
  undefined4 uVar3;
  int iVar4;
  short sVar5;
  undefined4 local_12;
  undefined4 local_e;
  undefined1 local_9;
  undefined1 local_8;
  undefined1 local_7;
  undefined1 local_6;
  undefined1 local_5;
  
  local_9 = 0x20;
  local_e = 0;
  local_12 = 0xffffffff;
  local_8 = 0;
  local_7 = 0;
  local_6 = 0;
  local_5 = 0;
  if (*param_1 != 0) {
    sVar5 = 0x18;
    while (sVar5 = sVar5 + -6, -1 < sVar5) {
      if ((ushort)*param_1 == *(ushort *)(sVar5 + 0x100b2e)) {
                    /* WARNING: Could not recover jumptable at 0x00100b2a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
        uVar3 = (*(code *)(sVar5 + 0x100b30))();
        return uVar3;
      }
    }
  }
  if (*param_1 == 0x30) {
    local_9 = 0x30;
    param_1 = param_1 + 1;
  }
  if (*param_1 == 0x2a) {
    puVar1 = (undefined4 *)*param_2;
    *param_2 = *param_2 + 4;
    local_e = *puVar1;
    param_1 = param_1 + 1;
  }
  else {
    iVar4 = FUN_001007bc(param_1,&local_e);
    param_1 = param_1 + iVar4;
  }
  if (*param_1 == 0x2e) {
    pbVar2 = param_1 + 1;
    if (*pbVar2 == 0x2a) {
      puVar1 = (undefined4 *)*param_2;
      *param_2 = *param_2 + 4;
      local_12 = *puVar1;
      param_1 = param_1 + 2;
    }
    else {
      iVar4 = FUN_001007bc(pbVar2,&local_12);
      param_1 = pbVar2 + iVar4;
    }
  }
  if (*param_1 == 0x6c) {
    param_1 = param_1 + 1;
  }
  else if (*param_1 == 0x68) {
    param_1 = param_1 + 1;
  }
  sVar5 = 0x30;
  do {
    sVar5 = sVar5 + -6;
    if (sVar5 < 0) {
      return 0;
    }
  } while ((ushort)*param_1 != *(ushort *)(sVar5 + 0x100c30));
                    /* WARNING: Could not recover jumptable at 0x00100c2c. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  uVar3 = (*(code *)(sVar5 + 0x100c32))();
  return uVar3;
}



/* ===== FUN_00100f46 @ 00100f46 (size 150) ===== */

void FUN_00100f46(code *param_1,byte *param_2,undefined4 param_3)

{
  byte *pbVar1;
  undefined4 local_e;
  byte *local_a;
  byte local_5;
  
  local_e = param_3;
  do {
    local_5 = *param_2;
    pbVar1 = param_2 + 1;
    if (local_5 == 0) {
      return;
    }
    if (local_5 != 0x25) goto LAB_00100f98;
    if (*pbVar1 == 0x25) {
      pbVar1 = param_2 + 2;
      goto LAB_00100f98;
    }
    param_2 = (byte *)FUN_00100ad0(pbVar1,&local_e,param_1);
    local_a = param_2;
    if (param_2 == (byte *)0x0) {
LAB_00100f98:
      param_2 = pbVar1;
      if ((DAT_0011d034 != 0) && ((local_5 & 0x80) != 0)) {
        (*param_1)(local_5);
        local_5 = *param_2;
        param_2 = param_2 + 1;
      }
      (*param_1)(local_5);
    }
  } while( true );
}



/* ===== FUN_00101540 @ 00101540 (size 50) ===== */

uint FUN_00101540(void)

{
  uint in_D0;
  ushort uVar3;
  uint uVar1;
  uint uVar2;
  uint in_D1;
  int iVar4;
  uint uVar5;
  uint uVar6;
  uint uVar7;
  bool bVar8;
  
  if ((int)in_D0 < 0) {
    if ((int)in_D1 < 0) {
      iVar4 = FUN_00101572();
      return -iVar4;
    }
    iVar4 = FUN_00101572();
    return -iVar4;
  }
  if ((int)in_D1 < 0) {
    uVar5 = FUN_00101572();
    return uVar5;
  }
  uVar5 = in_D1 << 0x10 | in_D1 >> 0x10;
  uVar3 = (ushort)(in_D1 >> 0x10);
  if (uVar3 == 0) {
    uVar3 = (ushort)(in_D0 >> 0x10);
    uVar5 = (uint)uVar3;
    if (uVar3 != 0) {
      uVar5 = uVar5 % (in_D1 & 0xffff) << 0x10;
    }
    return CONCAT22((short)(uVar5 >> 0x10),(short)in_D0) % (in_D1 & 0xffff);
  }
  uVar7 = 0x10;
  if (uVar3 < 0x80) {
    uVar5 = uVar5 << 8 | (in_D1 & 0xffff) >> 8;
    uVar7 = 8;
  }
  if ((ushort)uVar5 < 0x800) {
    uVar5 = uVar5 << 4 | uVar5 >> 0x1c;
    uVar7 = (uint)(ushort)((short)uVar7 - 4);
  }
  if ((ushort)uVar5 < 0x2000) {
    uVar5 = uVar5 << 2 | uVar5 >> 0x1e;
    uVar7 = (uint)(ushort)((short)uVar7 - 2);
  }
  if (-1 < (short)uVar5) {
    uVar5 = uVar5 << 1 | uVar5 >> 0x1f;
    uVar7 = (uint)(ushort)((short)uVar7 - 1);
  }
  uVar1 = in_D0 >> (uVar7 & 0x3f);
  uVar2 = CONCAT22((short)(uVar1 % (uVar5 & 0xffff)),(short)((in_D0 << 0x10) >> (uVar7 & 0x3f)));
  uVar6 = uVar5 << 0x10 | uVar5 >> 0x10;
  uVar1 = (uVar1 / (uVar5 & 0xffff) & 0xffff) * (uVar5 >> 0x10);
  uVar5 = uVar2 - uVar1;
  if (uVar2 < uVar1) {
    bVar8 = CARRY4(uVar6,uVar5);
    uVar5 = uVar6 + uVar5;
    do {
    } while (!bVar8);
  }
  uVar5 = uVar5 << (uVar7 & 0x3f) | uVar5 >> 0x20 - (uVar7 & 0x3f);
  return uVar5 << 0x10 | uVar5 >> 0x10;
}



/* ===== FUN_00101572 @ 00101572 (size 146) ===== */

ulonglong FUN_00101572(void)

{
  uint in_D0;
  uint uVar1;
  ushort uVar3;
  uint uVar2;
  short sVar4;
  uint in_D1;
  uint uVar5;
  uint uVar6;
  uint uVar7;
  bool bVar8;
  
  uVar5 = in_D1 << 0x10 | in_D1 >> 0x10;
  uVar3 = (ushort)(in_D1 >> 0x10);
  if (uVar3 == 0) {
    uVar1 = in_D0 << 0x10 | in_D0 >> 0x10;
    uVar7 = in_D1 & 0xffff;
    uVar3 = (ushort)(in_D0 >> 0x10);
    uVar5 = (uint)uVar3;
    if (uVar3 != 0) {
      uVar1 = uVar5 / uVar7;
      uVar5 = uVar5 % uVar7 << 0x10;
      uVar1 = CONCAT22((short)in_D0,(short)uVar1);
    }
    uVar5 = CONCAT22((short)(uVar5 >> 0x10),(short)(uVar1 >> 0x10));
    return CONCAT44(CONCAT22((short)uVar1,(short)(uVar5 / uVar7)),uVar5 % uVar7);
  }
  uVar7 = 0x10;
  if (uVar3 < 0x80) {
    uVar5 = uVar5 << 8 | (in_D1 & 0xffff) >> 8;
    uVar7 = 8;
  }
  if ((ushort)uVar5 < 0x800) {
    uVar5 = uVar5 << 4 | uVar5 >> 0x1c;
    uVar7 = (uint)(ushort)((short)uVar7 - 4);
  }
  if ((ushort)uVar5 < 0x2000) {
    uVar5 = uVar5 << 2 | uVar5 >> 0x1e;
    uVar7 = (uint)(ushort)((short)uVar7 - 2);
  }
  if (-1 < (short)uVar5) {
    uVar5 = uVar5 << 1 | uVar5 >> 0x1f;
    uVar7 = (uint)(ushort)((short)uVar7 - 1);
  }
  uVar2 = in_D0 >> (uVar7 & 0x3f);
  uVar1 = uVar2 / (uVar5 & 0xffff);
  sVar4 = (short)uVar1;
  uVar2 = CONCAT22((short)(uVar2 % (uVar5 & 0xffff)),(short)((in_D0 << 0x10) >> (uVar7 & 0x3f)));
  uVar6 = uVar5 << 0x10 | uVar5 >> 0x10;
  uVar1 = (uVar1 & 0xffff) * (uVar5 >> 0x10);
  uVar5 = uVar2 - uVar1;
  if (uVar2 < uVar1) {
    sVar4 = sVar4 + -1;
    bVar8 = CARRY4(uVar6,uVar5);
    uVar5 = uVar6 + uVar5;
    do {
    } while (!bVar8);
  }
  uVar5 = uVar5 << (uVar7 & 0x3f) | uVar5 >> 0x20 - (uVar7 & 0x3f);
  return (ulonglong)CONCAT24(sVar4,uVar5 << 0x10 | uVar5 >> 0x10);
}



/* ===== FUN_00101604 @ 00101604 (size 32) ===== */

int FUN_00101604(void)

{
  uint in_D0;
  uint in_D1;
  
  return (uint)(ushort)((short)(in_D1 >> 0x10) * (short)in_D0 +
                       (short)(in_D0 >> 0x10) * (short)in_D1) * 0x10000 +
         (in_D0 & 0xffff) * (in_D1 & 0xffff);
}



/* ===== FUN_00101624 @ 00101624 (size 20) ===== */

undefined4 FUN_00101624(undefined4 *param_1)

{
  undefined4 in_D1;
  undefined4 unaff_D2;
  undefined4 unaff_D3;
  undefined4 unaff_D4;
  undefined4 unaff_D5;
  undefined4 unaff_D6;
  undefined4 unaff_D7;
  undefined4 in_A1;
  undefined4 unaff_A2;
  undefined4 unaff_A3;
  undefined4 unaff_A5;
  undefined4 unaff_A6;
  undefined4 in_stack_00000000;
  
  param_1[1] = in_D1;
  param_1[2] = unaff_D2;
  param_1[3] = unaff_D3;
  param_1[4] = unaff_D4;
  param_1[5] = unaff_D5;
  param_1[6] = unaff_D6;
  param_1[7] = unaff_D7;
  param_1[8] = in_A1;
  param_1[9] = unaff_A2;
  param_1[10] = unaff_A3;
  param_1[0xb] = &DAT_0011d000;
  param_1[0xc] = unaff_A5;
  param_1[0xd] = unaff_A6;
  param_1[0xe] = register0x0000003c;
  *param_1 = in_stack_00000000;
  return 0;
}



/* ===== FUN_00101638 @ 00101638 (size 26) ===== */

undefined8 FUN_00101638(undefined4 *param_1,int param_2)

{
  undefined4 uVar1;
  
  if (param_2 == 0) {
    param_2 = 1;
  }
  uVar1 = param_1[1];
  *(undefined4 *)param_1[0xe] = *param_1;
  return CONCAT44(param_2,uVar1);
}



/* ===== FUN_00101654 @ 00101654 (size 32) ===== */

undefined4 FUN_00101654(char *param_1,char *param_2)

{
  char cVar1;
  
  do {
    cVar1 = *param_1;
    if (cVar1 != *param_2) {
      if (cVar1 <= *param_2) {
        return 0xffffffff;
      }
      return 1;
    }
    param_1 = param_1 + 1;
    param_2 = param_2 + 1;
  } while (cVar1 != '\0');
  return 0;
}



/* ===== FUN_00101674 @ 00101674 (size 18) ===== */

char * FUN_00101674(char *param_1,char *param_2)

{
  char cVar1;
  char *pcVar2;
  
  pcVar2 = param_1;
  do {
    cVar1 = *param_2;
    *pcVar2 = cVar1;
    param_2 = param_2 + 1;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  return param_1;
}



/* ===== FUN_00101688 @ 00101688 (size 18) ===== */

int FUN_00101688(char *param_1)

{
  char *pcVar1;
  char *pcVar2;
  
  pcVar1 = param_1;
  do {
    pcVar2 = pcVar1;
    pcVar1 = pcVar2 + 1;
  } while (*pcVar2 != '\0');
  return (int)pcVar2 - (int)param_1;
}



/* ===== FUN_0010169c @ 0010169c (size 72) ===== */

void FUN_0010169c(undefined4 param_1,undefined4 param_2)

{
  int iVar1;
  int *piVar2;
  
  piVar2 = &DAT_001231a8;
  for (iVar1 = 0; iVar1 < DAT_001200d4; iVar1 = iVar1 + 1) {
    if ((*piVar2 != 0) && ((*piVar2 & 4) == 0)) {
      FUN_0010182c(piVar2[1]);
    }
    piVar2 = piVar2 + 2;
  }
  FUN_0010012e(param_1,param_2);
  return;
}



/* ===== FUN_001016e4 @ 001016e4 (size 78) ===== */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

uint FUN_001016e4(void)

{
  uint uVar1;
  int iVar2;
  
  uVar1 = (**(code **)(AbsExecBase + -0x132))();    /* = SysBase.SetSignal() */
  uVar1 = uVar1 & 0x3000;
  if (uVar1 == 0) {
    uVar1 = 0;
  }
  else if (DAT_0011d030 != (code *)0x0) {
    iVar2 = (*DAT_0011d030)();
    if (iVar2 == 0) {
      uVar1 = 0;
    }
    else {
      FUN_0010169c(0x14,0);
    }
  }
  return uVar1;
}



/* ===== FUN_00101740 @ 00101740 (size 80) ===== */

int FUN_00101740(void)

{
  int iVar1;
  
  if (DAT_0011d030 != 0) {
    FUN_001016e4();
  }
  DAT_0011d018 = 0;
  iVar1 = (**(code **)(DOSBase + -0x30))();    /* = DOSBase.Write() */
  if (iVar1 == -1) {
    DAT_0011d018 = (**(code **)(DOSBase + -0x84))();    /* = DOSBase.IoErr() */
    DAT_00120038 = 5;
  }
  return iVar1;
}



/* ===== FUN_00101798 @ 00101798 (size 146) ===== */

int FUN_00101798(undefined4 param_1,int param_2,int param_3)

{
  int iVar1;
  
  if (DAT_0011d030 != 0) {
    FUN_001016e4();
  }
  DAT_0011d018 = 0;
  iVar1 = (**(code **)(DOSBase + -0x42))();    /* = DOSBase.Seek() */
  if (iVar1 == -1) {
    DAT_0011d018 = (**(code **)(DOSBase + -0x84))();    /* = DOSBase.IoErr() */
    DAT_00120038 = 0x16;
  }
  if (param_3 == 2) {
    param_3 = (**(code **)(DOSBase + -0x42))();    /* = DOSBase.Seek() */
  }
  else if (param_3 == 1) {
    param_3 = param_2 + iVar1;
  }
  else if (param_3 == 0) {
    param_3 = param_2;
  }
  return param_3;
}



/* ===== FUN_0010182c @ 0010182c (size 32) ===== */

undefined4 FUN_0010182c(void)

{
  if (DAT_0011d030 != 0) {
    FUN_001016e4();
  }
  (**(code **)(DOSBase + -0x24))();    /* = DOSBase.Close() */
  return 0;
}



/* ===== FUN_00102000 @ 00102000 (size 174) ===== */
/* strings: cnet-configuration */

undefined4 FUN_00102000(void)

{
  int iVar1;
  short local_e;
  
  DAT_00120134 = 0;
  iVar1 = thunk_FUN_0011a41e(s_cnet_configuration_0011d456);
  if (iVar1 == 0) {
    thunk_FUN_00101674(&DAT_00120108,&DAT_0011d46a);
    DAT_00120118 = 400000;
    thunk_FUN_00101674(&DAT_0012011c,&DAT_0011d46c);
    DAT_0012012c = 0x4b;
    DAT_0012012e = 0x4b0;
    DAT_00120130 = 4;
    DAT_00120132 = 8;
  }
  else {
    for (local_e = 0; local_e < 0x36; local_e = local_e + 1) {
      (&DAT_00120108)[local_e] = *(undefined1 *)(iVar1 + local_e);
    }
    thunk_FUN_0011a238(iVar1);
  }
  thunk_FUN_00114050(DAT_00120132);
  thunk_FUN_00101674(&DAT_00120244,&DAT_00120134);
  return 1;
}



/* ===== FUN_001020ae @ 001020ae (size 204) ===== */

void FUN_001020ae(void)

{
  thunk_FUN_0012b1b0(DAT_001200fc,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  if (DAT_0011d078 != (undefined4 *)0x0) {
    thunk_FUN_0012b1b0(*DAT_0011d078,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  if (DAT_0011d07c != (undefined4 *)0x0) {
    thunk_FUN_0012b1b0(*DAT_0011d07c,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  if (DAT_00121650 != 0) {
    thunk_FUN_0012b1b0(DAT_00121650,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  if (DAT_00121698 != 0) {
    thunk_FUN_0012b1b0(DAT_00121698,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  if (DAT_0011fd70 != 0) {
    thunk_FUN_0012b1b0(DAT_0011fd70,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  return;
}



/* ===== FUN_0010217a @ 0010217a (size 162) ===== */

void FUN_0010217a(undefined4 param_1)

{
  thunk_FUN_0012b1d0(DAT_001200fc,0xffffffff,param_1);
  if (DAT_0011d078 != (undefined4 *)0x0) {
    thunk_FUN_0012b1d0(*DAT_0011d078,0xffffffff,param_1);
  }
  if (DAT_0011d07c != (undefined4 *)0x0) {
    thunk_FUN_0012b1d0(*DAT_0011d07c,0xffffffff,param_1);
  }
  if (DAT_00121650 != 0) {
    thunk_FUN_0012b1d0(DAT_00121650,0xffffffff,param_1);
  }
  if (DAT_00121698 != 0) {
    thunk_FUN_0012b1d0(DAT_00121698,0xffffffff,param_1);
  }
  if (DAT_0011fd70 != 0) {
    thunk_FUN_0012b1d0(DAT_0011fd70,0xffffffff,param_1);
  }
  return;
}



/* ===== FUN_0010221c @ 0010221c (size 96) ===== */

void FUN_0010221c(void)

{
  thunk_FUN_0012b014(DAT_001200fc);
  if (DAT_0011d078 != (undefined4 *)0x0) {
    thunk_FUN_0012b014(*DAT_0011d078);
  }
  if (DAT_0011d07c != (undefined4 *)0x0) {
    thunk_FUN_0012b014(*DAT_0011d07c);
  }
  if (DAT_00121650 != 0) {
    thunk_FUN_0012b014(DAT_00121650);
  }
  if (DAT_00121698 != 0) {
    thunk_FUN_0012b014(DAT_00121698);
  }
  if (DAT_0011fd70 != 0) {
    thunk_FUN_0012b014(DAT_0011fd70);
  }
  return;
}



/* ===== FUN_0010227c @ 0010227c (size 64) ===== */

void FUN_0010227c(int *param_1)

{
  int iVar1;
  
  while( true ) {
    iVar1 = *param_1;
    if (iVar1 == 0xffff) break;
    if (*(short *)(param_1 + 1) == 0) {
      thunk_FUN_0012b0f4(DAT_001200fc,iVar1,iVar1);
    }
    else {
      thunk_FUN_0012b128(DAT_001200fc,iVar1);
    }
    param_1 = (int *)((int)param_1 + 6);
  }
  return;
}



/* ===== FUN_001022bc @ 001022bc (size 152) ===== */

void FUN_001022bc(undefined4 *param_1,int param_2)

{
  short local_6;
  
  local_6 = 0;
  while( true ) {
    if (4 < local_6) break;
    if (*(char *)(param_2 + local_6) == '\0') {
      if ((*(ushort *)((int)param_1 + local_6 * 0x34 + 0xec2) & 0x100) == 0) {
        thunk_FUN_0012b0d8((int)param_1 + local_6 * 0x34 + 0xeb6,*param_1,0);
      }
    }
    else if ((*(ushort *)((int)param_1 + local_6 * 0x34 + 0xec2) & 0x100) != 0) {
      thunk_FUN_0012b10c((int)param_1 + local_6 * 0x34 + 0xeb6,*param_1,0);
    }
    local_6 = local_6 + 1;
  }
  return;
}



/* ===== FUN_00102354 @ 00102354 (size 152) ===== */

void FUN_00102354(undefined4 *param_1,int param_2)

{
  short local_6;
  
  local_6 = 0;
  while( true ) {
    if (5 < local_6) break;
    if (*(char *)(param_2 + local_6) == '\0') {
      if ((*(ushort *)(param_1 + local_6 * 0xd + 0x1e7) & 0x100) == 0) {
        thunk_FUN_0012b0d8(param_1 + local_6 * 0xd + 0x1e4,*param_1,0);
      }
    }
    else if ((*(ushort *)(param_1 + local_6 * 0xd + 0x1e7) & 0x100) != 0) {
      thunk_FUN_0012b10c(param_1 + local_6 * 0xd + 0x1e4,*param_1,0);
    }
    local_6 = local_6 + 1;
  }
  return;
}



/* ===== FUN_001023ec @ 001023ec (size 498) ===== */
/* strings: Compunet - courier | Compunet - logging on | Compunet - offline | Compunet - online | Dir or Goto for new directory | Send to upload, Done to finish */

void FUN_001023ec(void)

{
  undefined *puVar1;
  
  if ((DAT_0011d46e == DAT_0011d070) && (DAT_0011d472 == DAT_0011d074)) {
    return;
  }
  DAT_0011d472 = DAT_0011d074;
  DAT_0011d46e = DAT_0011d070;
  switch(DAT_0011d070) {
  case 0:
    FUN_0010227c(&DAT_0011d236);
    FUN_0010217a(s_Compunet___offline_0011d476);
    break;
  case 1:
    FUN_0010217a(s_Compunet___logging_on_0011d48a);
    FUN_0010227c(&DAT_0011d26c);
    break;
  case 2:
    goto LAB_00102474;
  case 3:
LAB_00102474:
    FUN_0010217a(s_Compunet___online_0011d4a0);
    if (DAT_0011d074 == 0) {
      puVar1 = &DAT_0011d2a2;
    }
    else {
      puVar1 = &DAT_0011d302;
    }
    FUN_0010227c(puVar1);
    break;
  case 4:
    goto LAB_001024c4;
  case 5:
    goto LAB_001024ae;
  case 6:
LAB_001024ae:
    FUN_0010217a(s_Compunet___courier_0011d4d0);
    FUN_0010227c(&DAT_0011d3c6);
    break;
  case 7:
LAB_001024c4:
    FUN_0010217a(s_Send_to_upload__Done_to_finish_0011d4e4);
    FUN_0010227c(&DAT_0011d420);
    break;
  case 8:
    FUN_0010217a(s_Dir_or_Goto_for_new_directory_0011d4b2);
    FUN_0010227c(&DAT_0011d356);
  }
  if (DAT_0011d07c == 0) goto switchD_001024ee_default;
  switch(DAT_0011d070) {
  case 0:
    break;
  case 1:
    break;
  case 2:
    if (DAT_0011d074 == 0) {
      puVar1 = &DAT_0011d2f6;
    }
    else {
      puVar1 = &DAT_0011d3aa;
    }
    FUN_001022bc(DAT_0011d07c,puVar1);
    break;
  case 3:
    FUN_001022bc(DAT_0011d07c,&DAT_0011d3af);
    break;
  case 4:
    goto LAB_00102552;
  case 5:
    goto LAB_00102542;
  case 6:
LAB_00102542:
    FUN_001022bc(DAT_0011d07c,&DAT_0011d41a);
    break;
  case 7:
LAB_00102552:
    FUN_001022bc(DAT_0011d07c,&DAT_0011d450);
    break;
  case 8:
    FUN_001022bc(DAT_0011d07c,&DAT_0011d3ba);
  }
switchD_001024ee_default:
  if (DAT_0011d078 == 0) {
    return;
  }
  switch(DAT_0011d070) {
  case 0:
    FUN_00102354(DAT_0011d078,&DAT_0011d266);
    break;
  case 1:
    FUN_00102354(DAT_0011d078,&DAT_0011d29c);
    break;
  case 2:
    goto LAB_001025aa;
  case 3:
    FUN_00102354(DAT_0011d078,&DAT_0011d3b4);
    break;
  case 4:
    goto LAB_001025ca;
  case 5:
    goto LAB_001025aa;
  case 6:
    goto LAB_001025aa;
  case 7:
LAB_001025ca:
    FUN_00102354(DAT_0011d078,&DAT_0011d3bf);
    break;
  case 8:
LAB_001025aa:
    FUN_00102354(DAT_0011d078,&DAT_0011d2fb);
  }
  return;
}



/* ===== FUN_001025de @ 001025de (size 208) ===== */
/* strings: CnetEditor */

undefined4 FUN_001025de(void)

{
  undefined4 uVar1;
  int iVar2;
  
  thunk_FUN_0011a000();
  DAT_00120142 = thunk_FUN_0011a75c(0,0);
  if (DAT_00120142 == 0) {
    thunk_FUN_0011a0b0();
    uVar1 = 0;
  }
  else {
    DAT_0011d06c = thunk_FUN_0011a868(s_CnetEditor_0011d504);
    if (DAT_0011d06c == 0) {
      thunk_FUN_0011a0b0();
      uVar1 = 0;
    }
    else {
      iVar2 = thunk_FUN_001280b4(s_CnetEditor_0011d510,0,DAT_0011d06c,4000);
      if (iVar2 == 0) {
        thunk_FUN_0011a0b0();
        uVar1 = 0;
      }
      else {
        DAT_00120154 = DAT_00120142;
        DAT_0012015a = 0;
        DAT_0012015c = DAT_001200f8;
        DAT_00120160 = DAT_00120258;
        DAT_00120164 = *(undefined4 *)(DAT_001200f0 + 0x98);
        thunk_FUN_001290f4(iVar2,&DAT_00120146);
        thunk_FUN_00129134(DAT_00120142);
        thunk_FUN_0012910c(DAT_00120142);
        if (DAT_0012015b == '\0') {
          DAT_0012013e = DAT_0012015c;
          DAT_00120168 = DAT_00120160;
          thunk_FUN_0011a00a();
          uVar1 = 1;
        }
        else {
          thunk_FUN_0011a0b0();
          uVar1 = 0;
        }
      }
    }
  }
  return uVar1;
}



/* ===== FUN_001026ae @ 001026ae (size 358) ===== */
/* strings: CnetTty | graphics.library | intuition.library */

void FUN_001026ae(void)

{
  int *piVar1;
  int iVar2;
  
  IntuitionBase = thunk_FUN_0011a290(s_intuition_library_0011d51c,0x21);
  if (IntuitionBase == 0) {
    thunk_FUN_0011a11e(0x14);
  }
  GfxBase = thunk_FUN_0011a290(s_graphics_library_0011d52e,0x21);
  if (GfxBase == 0) {
    thunk_FUN_0011a11e(0x14);
  }
  DAT_001200f8 = thunk_FUN_0011a4e0(s_Compunet_0011d098 + 10);
  if (DAT_001200f8 == 0) {
    thunk_FUN_0011a11e(0x14);
  }
  thunk_FUN_0012a01c(DAT_001200f8 + 0x2c,&DAT_0011d0c2,0x10);
  DAT_0011d100 = DAT_001200f8;
  DAT_001200fc = thunk_FUN_0011a534(&DAT_0011d0e2);
  if (DAT_001200fc == 0) {
    thunk_FUN_0011a11e(0x14);
  }
  FUN_001020ae();
  DAT_00120100 = *(int *)(DAT_001200fc + 0x56);
  DAT_00120104 = 1 << (*(byte *)(DAT_00120100 + 0xf) & 0x3f);
  piVar1 = (int *)thunk_FUN_0011b000(&PTR_DAT_0011d172);
  DAT_001201ae = *piVar1;
  DAT_001201b2 = piVar1[1];
  if (DAT_001201ae == 0) {
    thunk_FUN_0011a11e(0x14);
  }
  thunk_FUN_0011a588(DAT_001200fc,DAT_001201ae);
  iVar2 = thunk_FUN_00106000();
  if (iVar2 == 0) {
    thunk_FUN_0011a11e(0x14);
  }
  DAT_001200f0 = thunk_FUN_0012907c(0);
  DAT_001200f4 = *(undefined4 *)(DAT_001200f0 + 0xb8);
  *(int *)(DAT_001200f0 + 0xb8) = DAT_001200fc;
  iVar2 = FUN_001025de();
  if (iVar2 == 0) {
    *(undefined4 *)(DAT_001200f0 + 0xb8) = DAT_001200f4;
    thunk_FUN_0011a11e(0x14);
  }
  FUN_00102000();
  iVar2 = thunk_FUN_0011a868(s_CnetTty_0011d540);
  if (iVar2 == 0) {
    thunk_FUN_0011a11e(0x14);
  }
  DAT_0012016c = iVar2 * 4 + 4;
  return;
}



/* ===== FUN_00102814 @ 00102814 (size 340) ===== */

void FUN_00102814(void)

{
  int iVar1;
  undefined4 uVar2;
  undefined4 uVar3;
  short sVar4;
  ushort uVar5;
  int iVar6;
  int iVar7;
  bool bVar9;
  undefined4 uVar8;
  
  uVar2 = DAT_0011d548;
  uVar3 = DAT_0011d54c;
  iVar6 = DAT_0011d550;
  do {
    while( true ) {
      do {
        DAT_0011d550 = iVar6;
        DAT_0011d54c = uVar3;
        DAT_0011d548 = uVar2;
        FUN_001023ec();
        while (iVar6 = thunk_FUN_0012910c(DAT_00120100), iVar6 != 0) {
          thunk_FUN_00129120(iVar6);
        }
        FUN_0010221c();
        thunk_FUN_00129134(DAT_00120100);
        iVar7 = thunk_FUN_0012910c(DAT_00120100);
        uVar2 = DAT_0011d548;
        uVar3 = DAT_0011d54c;
        iVar6 = DAT_0011d550;
      } while (iVar7 == 0);
      iVar1 = *(int *)(iVar7 + 0x14);
      sVar4 = *(short *)(iVar7 + 0x18);
      uVar5 = *(ushort *)(iVar7 + 0x1a);
      iVar6 = *(int *)(iVar7 + 0x1c);
      uVar2 = *(undefined4 *)(iVar7 + 0x24);
      uVar3 = *(undefined4 *)(iVar7 + 0x28);
      thunk_FUN_00129120(iVar7);
      FUN_001020ae();
      if (iVar1 == 0x400) break;
      if (iVar1 == 0x20) {
        if ((iVar6 == DAT_0011d550) &&
           (iVar7 = thunk_FUN_0012b050(DAT_0011d548,DAT_0011d54c,uVar2,uVar3), iVar7 != 0)) {
          bVar9 = true;
        }
        else {
          bVar9 = false;
        }
        uVar8 = 0;
        if (bVar9) {
          if ((uVar5 & 1) == 0) {
            uVar8 = 1;
          }
          else {
            uVar8 = 2;
          }
        }
        (**(code **)(iVar6 + 0x2c))(iVar6,uVar8,uVar8);
      }
      else if ((iVar1 == 0x100) && (sVar4 != -1)) {
        thunk_FUN_0011b478(&DAT_001201ae,sVar4);
      }
    }
    if (((sVar4 == 0x5f) && ((uVar5 & 0x40) != 0)) && (DAT_0011d070 != 0)) {
      thunk_FUN_00101638(&DAT_00120170,1);
    }
  } while( true );
}



/* ===== FUN_00102968 @ 00102968 (size 126) ===== */

void FUN_00102968(void)

{
  char cVar1;
  
  do {
    cVar1 = thunk_FUN_0011a0b0();
  } while (DAT_001201ac <= cVar1);
  thunk_FUN_0011a000();
  if (DAT_0011d080 != 0) {
    thunk_FUN_001291d0(DAT_00120168 + 0xe);
    *(byte *)(DAT_0011d080 + 0x11) = *(byte *)(DAT_0011d080 + 0x11) & 0xfb;
    thunk_FUN_001291e4(DAT_00120168 + 0xe);
    DAT_0011d080 = 0;
  }
  DAT_0011d074 = 0;
  DAT_0011d07c = 0;
  DAT_0011d570 = 0;
  DAT_0011d078 = 0;
  DAT_00121650 = 0;
  DAT_00121698 = 0;
  DAT_0011fd70 = 0;
  DAT_0011f120 = 0;
  DAT_0011f124 = 0;
  DAT_0011f128 = 0;
  DAT_0011d070 = 0;
  return;
}



/* ===== FUN_001029e6 @ 001029e6 (size 36) ===== */

void FUN_001029e6(void)

{
  int iVar1;
  
  FUN_001026ae();
  DAT_001201ac = thunk_FUN_0011a000();
  iVar1 = thunk_FUN_00101624(&DAT_00120170);
  if (iVar1 != 0) {
    FUN_00102968();
  }
  FUN_00102814();
  return;
}



/* ===== thunk_FUN_001290f4 @ 00102a78 (size 6) ===== */

void thunk_FUN_001290f4(void)

{
  (**(code **)(SysBase + -0x16e))();    /* = SysBase.PutMsg() */
  return;
}



/* ===== thunk_FUN_00129120 @ 00102a7e (size 6) ===== */

void thunk_FUN_00129120(void)

{
  (**(code **)(SysBase + -0x17a))();    /* = SysBase.ReplyMsg() */
  return;
}



/* ===== thunk_FUN_0012b1d0 @ 00102a84 (size 6) ===== */

void thunk_FUN_0012b1d0(void)

{
  (**(code **)(IntuitionBase + -0x114))();    /* = IntuitionBase.SetWindowTitles() */
  return;
}



/* ===== thunk_FUN_0012b128 @ 00102a8a (size 6) ===== */

void thunk_FUN_0012b128(void)

{
  (**(code **)(IntuitionBase + -0xc0))();    /* = IntuitionBase.OnMenu() */
  return;
}



/* ===== thunk_FUN_0011b000 @ 00102a90 (size 6) ===== */

undefined1 * thunk_FUN_0011b000(undefined4 *param_1)

{
  uint uVar1;
  short sVar4;
  undefined4 uVar2;
  int iVar3;
  undefined2 uVar5;
  int **ppiVar6;
  undefined1 *puVar7;
  int *piStack_50;
  ushort *puStack_4c;
  ushort *puStack_48;
  undefined1 *puStack_44;
  undefined1 *puStack_40;
  undefined1 *puStack_3c;
  undefined1 *puStack_38;
  int *piStack_34;
  int *piStack_30;
  int *piStack_2c;
  int *piStack_28;
  int *piStack_24;
  undefined4 uStack_20;
  uint uStack_1c;
  int iStack_18;
  uint uStack_14;
  int iStack_10;
  int iStack_c;
  int iStack_8;
  
  piStack_50 = (int *)0x0;
  puStack_4c = (ushort *)0x0;
  iStack_8 = *(int *)((int)param_1 + 4);
  if (*(int *)((int)param_1 + 4) == 0) {
    sVar4 = 7;
    ppiVar6 = &piStack_50;
    puVar7 = &DAT_0011ff2c;
    do {
      *puVar7 = *(undefined1 *)ppiVar6;
      sVar4 = sVar4 + -1;
      ppiVar6 = (int **)((int)ppiVar6 + 1);
      puVar7 = puVar7 + 1;
    } while (sVar4 != -1);
  }
  else {
    param_1 = (undefined4 *)((int)param_1 + 0xe);
    thunk_FUN_0011a000();
    puStack_4c = (ushort *)thunk_FUN_0011a1ee(0x600,0);
    if (puStack_4c == (ushort *)0x0) {
      thunk_FUN_0011a0b0();
      sVar4 = 7;
      ppiVar6 = &piStack_50;
      puVar7 = &DAT_0011ff2c;
      do {
        *puVar7 = *(undefined1 *)ppiVar6;
        sVar4 = sVar4 + -1;
        ppiVar6 = (int **)((int)ppiVar6 + 1);
        puVar7 = puVar7 + 1;
      } while (sVar4 != -1);
    }
    else {
      puStack_48 = puStack_4c;
      uVar2 = thunk_FUN_00101604();
      piStack_50 = (int *)thunk_FUN_0011a1ee(uVar2,0);
      if (piStack_50 == (int *)0x0) {
        thunk_FUN_0011a0b0();
        sVar4 = 7;
        ppiVar6 = &piStack_50;
        puVar7 = &DAT_0011ff2c;
        do {
          *puVar7 = *(undefined1 *)ppiVar6;
          sVar4 = sVar4 + -1;
          ppiVar6 = (int **)((int)ppiVar6 + 1);
          puVar7 = puVar7 + 1;
        } while (sVar4 != -1);
      }
      else {
        piStack_24 = piStack_50;
        for (iStack_c = 0; iStack_c < iStack_8; iStack_c = iStack_c + 1) {
          if (iStack_8 == iStack_c + 1) {
            iVar3 = 0;
          }
          else {
            iVar3 = (int)piStack_24 + 0x1e;
          }
          *piStack_24 = iVar3;
          sVar4 = thunk_FUN_00101604();
          *(short *)(piStack_24 + 1) = sVar4 + 10;
          *(undefined2 *)((int)piStack_24 + 6) = 0;
          *(undefined2 *)(piStack_24 + 2) = 100;
          *(undefined2 *)((int)piStack_24 + 10) = 10;
          *(undefined2 *)(piStack_24 + 3) = 1;
          *(undefined4 *)((int)piStack_24 + 0xe) = *param_1;
          iStack_10 = param_1[1];
          uVar2 = thunk_FUN_00101604();
          piStack_28 = (int *)thunk_FUN_0011a1ee(uVar2,0);
          uVar2 = thunk_FUN_00101604();
          puStack_38 = (undefined1 *)thunk_FUN_0011a1ee(uVar2,0);
          if ((piStack_28 == (int *)0x0) || (puStack_38 == (undefined1 *)0x0)) {
            thunk_FUN_0011a0b0();
            piStack_50 = (int *)0x0;
            sVar4 = 7;
            ppiVar6 = &piStack_50;
            puVar7 = &DAT_0011ff2c;
            do {
              *puVar7 = *(undefined1 *)ppiVar6;
              sVar4 = sVar4 + -1;
              ppiVar6 = (int **)((int)ppiVar6 + 1);
              puVar7 = puVar7 + 1;
            } while (sVar4 != -1);
            goto LAB_0011b470;
          }
          *(int **)((int)piStack_24 + 0x12) = piStack_28;
          param_1 = (undefined4 *)((int)param_1 + 0xe);
          piStack_30 = piStack_28;
          puStack_40 = puStack_38;
          for (uStack_14 = 0; uVar1 = uStack_14, (int)uStack_14 < iStack_10;
              uStack_14 = uStack_14 + 1) {
            if (*(char *)(param_1 + 3) == '\0') {
              uStack_20 = 0x52;
            }
            else {
              uStack_20 = 0x56;
            }
            if (iStack_10 == uStack_14 + 1) {
              iVar3 = 0;
            }
            else {
              iVar3 = (int)piStack_30 + 0x22;
            }
            *piStack_30 = iVar3;
            *(undefined2 *)(piStack_30 + 1) = 0;
            uVar5 = thunk_FUN_00101604();
            *(undefined2 *)((int)piStack_30 + 6) = uVar5;
            *(undefined2 *)(piStack_30 + 2) = 100;
            *(undefined2 *)((int)piStack_30 + 10) = 10;
            *(short *)(piStack_30 + 3) = (short)uStack_20;
            *(undefined4 *)((int)piStack_30 + 0xe) = 0;
            *(undefined1 **)((int)piStack_30 + 0x12) = puStack_40;
            *(undefined4 *)((int)piStack_30 + 0x16) = 0;
            *(undefined1 *)((int)piStack_30 + 0x1a) = *(undefined1 *)(param_1 + 3);
            *puStack_40 = 0;
            puStack_40[1] = 1;
            puStack_40[2] = 0;
            *(undefined2 *)(puStack_40 + 4) = 0;
            *(undefined2 *)(puStack_40 + 6) = 0;
            *(undefined4 *)(puStack_40 + 8) = 0;
            *(undefined4 *)(puStack_40 + 0xc) = *param_1;
            *(undefined4 *)(puStack_40 + 0x10) = 0;
            if (param_1[2] != 0) {
              *puStack_48 = (ushort)((uVar1 & 0x3f) << 5) | (ushort)iStack_c & 0x1f | 0xf800;
              *(undefined4 *)(puStack_48 + 1) = param_1[2];
              puStack_48 = puStack_48 + 3;
            }
            iStack_18 = param_1[1];
            param_1 = (undefined4 *)((int)param_1 + 0xe);
            if (iStack_18 == 0) {
              piStack_30[7] = 0;
            }
            else {
              uVar2 = thunk_FUN_00101604();
              piStack_2c = (int *)thunk_FUN_0011a1ee(uVar2,0);
              uVar2 = thunk_FUN_00101604();
              puStack_3c = (undefined1 *)thunk_FUN_0011a1ee(uVar2,0);
              if ((piStack_2c == (int *)0x0) || (puStack_3c == (undefined1 *)0x0)) {
                thunk_FUN_0011a0b0();
                piStack_50 = (int *)0x0;
                sVar4 = 7;
                ppiVar6 = &piStack_50;
                puVar7 = &DAT_0011ff2c;
                do {
                  *puVar7 = *(undefined1 *)ppiVar6;
                  sVar4 = sVar4 + -1;
                  ppiVar6 = (int **)((int)ppiVar6 + 1);
                  puVar7 = puVar7 + 1;
                } while (sVar4 != -1);
                goto LAB_0011b470;
              }
              piStack_30[7] = (int)piStack_2c;
              piStack_34 = piStack_2c;
              puStack_44 = puStack_3c;
              for (uStack_1c = 0; uVar1 = uStack_1c, (int)uStack_1c < iStack_18;
                  uStack_1c = uStack_1c + 1) {
                if (*(char *)(param_1 + 3) == '\0') {
                  uStack_20 = 0x52;
                }
                else {
                  uStack_20 = 0x56;
                }
                if (iStack_18 == uStack_1c + 1) {
                  iVar3 = 0;
                }
                else {
                  iVar3 = (int)piStack_34 + 0x22;
                }
                *piStack_34 = iVar3;
                *(undefined2 *)(piStack_34 + 1) = 0x46;
                sVar4 = thunk_FUN_00101604();
                *(short *)((int)piStack_34 + 6) = sVar4 + 5;
                *(undefined2 *)(piStack_34 + 2) = 100;
                *(undefined2 *)((int)piStack_34 + 10) = 10;
                *(short *)(piStack_34 + 3) = (short)uStack_20;
                *(undefined4 *)((int)piStack_34 + 0xe) = 0;
                *(undefined1 **)((int)piStack_34 + 0x12) = puStack_44;
                *(undefined4 *)((int)piStack_34 + 0x16) = 0;
                *(undefined1 *)((int)piStack_34 + 0x1a) = *(undefined1 *)(param_1 + 3);
                piStack_34[7] = 0;
                *puStack_44 = 0;
                puStack_44[1] = 1;
                puStack_44[2] = 0;
                *(undefined2 *)(puStack_44 + 4) = 0;
                *(undefined2 *)(puStack_44 + 6) = 0;
                *(undefined4 *)(puStack_44 + 8) = 0;
                *(undefined4 *)(puStack_44 + 0xc) = *param_1;
                *(undefined4 *)(puStack_44 + 0x10) = 0;
                if (param_1[2] != 0) {
                  *puStack_48 = (ushort)((uVar1 & 0x1f) << 0xb) |
                                (ushort)((uStack_14 & 0x3f) << 5) | (ushort)iStack_c & 0x1f;
                  *(undefined4 *)(puStack_48 + 1) = param_1[2];
                  puStack_48 = puStack_48 + 3;
                }
                param_1 = (undefined4 *)((int)param_1 + 0xe);
                piStack_34 = (int *)((int)piStack_34 + 0x22);
                puStack_44 = puStack_44 + 0x14;
              }
            }
            piStack_30 = (int *)((int)piStack_30 + 0x22);
            puStack_40 = puStack_40 + 0x14;
          }
          piStack_24 = (int *)((int)piStack_24 + 0x1e);
        }
        *puStack_48 = 0xffff;
        thunk_FUN_0011a00a();
        sVar4 = 7;
        ppiVar6 = &piStack_50;
        puVar7 = &DAT_0011ff2c;
        do {
          *puVar7 = *(undefined1 *)ppiVar6;
          sVar4 = sVar4 + -1;
          ppiVar6 = (int **)((int)ppiVar6 + 1);
          puVar7 = puVar7 + 1;
        } while (sVar4 != -1);
      }
    }
  }
LAB_0011b470:
  return &DAT_0011ff2c;
}



/* ===== thunk_FUN_00101624 @ 00102a96 (size 6) ===== */

undefined4 thunk_FUN_00101624(undefined4 *param_1)

{
  undefined4 in_D1;
  undefined4 unaff_D2;
  undefined4 unaff_D3;
  undefined4 unaff_D4;
  undefined4 unaff_D5;
  undefined4 unaff_D6;
  undefined4 unaff_D7;
  undefined4 in_A1;
  undefined4 unaff_A2;
  undefined4 unaff_A3;
  undefined4 unaff_A5;
  undefined4 unaff_A6;
  undefined4 in_stack_00000000;
  
  param_1[1] = in_D1;
  param_1[2] = unaff_D2;
  param_1[3] = unaff_D3;
  param_1[4] = unaff_D4;
  param_1[5] = unaff_D5;
  param_1[6] = unaff_D6;
  param_1[7] = unaff_D7;
  param_1[8] = in_A1;
  param_1[9] = unaff_A2;
  param_1[10] = unaff_A3;
  param_1[0xb] = &DAT_0011d000;
  param_1[0xc] = unaff_A5;
  param_1[0xd] = unaff_A6;
  param_1[0xe] = register0x0000003c;
  *param_1 = in_stack_00000000;
  return 0;
}



/* ===== thunk_FUN_0012b014 @ 00102a9c (size 6) ===== */

void thunk_FUN_0012b014(void)

{
  (**(code **)(IntuitionBase + -0x3c))();    /* = IntuitionBase.ClearPointer() */
  return;
}



/* ===== thunk_FUN_00129134 @ 00102aa2 (size 6) ===== */

void thunk_FUN_00129134(void)

{
  (**(code **)(SysBase + -0x180))();    /* = SysBase.WaitPort() */
  return;
}



/* ===== thunk_FUN_0011a588 @ 00102aa8 (size 6) ===== */

void thunk_FUN_0011a588(undefined4 param_1,undefined4 param_2)

{
  thunk_FUN_0012b198(param_1,param_2);
  FUN_0011a16c(&LAB_0011a8ce,param_1,0);
  return;
}



/* ===== thunk_FUN_0012907c @ 00102aae (size 6) ===== */

void thunk_FUN_0012907c(void)

{
  (**(code **)(SysBase + -0x126))();    /* = SysBase.FindTask() */
  return;
}



/* ===== thunk_FUN_001280b4 @ 00102ab4 (size 6) ===== */

void thunk_FUN_001280b4(void)

{
  (**(code **)(DOSBase + -0x8a))();    /* = DOSBase.CreateProc() */
  return;
}



/* ===== thunk_FUN_0012910c @ 00102aba (size 6) ===== */

void thunk_FUN_0012910c(void)

{
  (**(code **)(SysBase + -0x174))();    /* = SysBase.GetMsg() */
  return;
}



/* ===== thunk_FUN_0011a290 @ 00102ac0 (size 6) ===== */

int thunk_FUN_0011a290(undefined4 param_1,undefined4 param_2)

{
  int iVar1;
  
  iVar1 = thunk_FUN_001291b8(param_1,param_2);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(&LAB_0011a976,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_0011a41e @ 00102acc (size 6) ===== */

int thunk_FUN_0011a41e(undefined4 param_1)

{
  int iVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  
  FUN_0011a000();
  iVar1 = FUN_0011a344(param_1,0xfffffffe);
  if (((iVar1 != 0) && (iVar2 = FUN_0011a1ee(0x104,0), iVar2 != 0)) &&
     (iVar3 = thunk_FUN_00128098(iVar1,iVar2), iVar3 != 0)) {
    FUN_0011a3a6(iVar1);
    iVar1 = *(int *)(iVar2 + 0x7c);
    FUN_0011a238(iVar2);
    iVar2 = FUN_0011a1ee(iVar1,0);
    if (((iVar2 != 0) && (iVar3 = FUN_0011a3c6(param_1,0x3ed), iVar3 != 0)) &&
       (iVar4 = thunk_FUN_00128030(iVar3,iVar2,iVar1), iVar4 == iVar1)) {
      FUN_0011a3fe(iVar3);
      FUN_0011a00a();
      return iVar2;
    }
  }
  FUN_0011a0b0();
  return 0;
}



/* ===== thunk_FUN_0012b0f4 @ 00102ad2 (size 6) ===== */

void thunk_FUN_0012b0f4(void)

{
  (**(code **)(IntuitionBase + -0xb4))();    /* = IntuitionBase.OffMenu() */
  return;
}



/* ===== thunk_FUN_0011b478 @ 00102ad8 (size 6) ===== */

undefined4 thunk_FUN_0011b478(int param_1,short param_2)

{
  undefined4 uVar1;
  short *psStack_8;
  
  psStack_8 = *(short **)(param_1 + 4);
  while( true ) {
    if (*psStack_8 == -1) {
      return 0;
    }
    if (*psStack_8 == param_2) break;
    psStack_8 = psStack_8 + 3;
  }
  uVar1 = (**(code **)(psStack_8 + 1))();
  return uVar1;
}



/* ===== thunk_FUN_00106000 @ 00102ade (size 6) ===== */

undefined4 thunk_FUN_00106000(void)

{
  byte bVar1;
  int iVar2;
  undefined4 uVar3;
  int iVar4;
  short sStack_8;
  short sStack_6;
  
  DAT_00120258 = thunk_FUN_0011a1ee(0x2000,2);
  if (DAT_00120258 == 0) {
    uVar3 = 0;
  }
  else {
    for (sStack_6 = 0; sStack_6 < 0x80; sStack_6 = sStack_6 + 1) {
      for (sStack_8 = 0; sStack_8 < 8; sStack_8 = sStack_8 + 1) {
        bVar1 = s_<fnn_b<_0011d9c0[(int)sStack_8 + sStack_6 * 8];
        *(ushort *)(sStack_8 * 2 + sStack_6 * 0x10 + DAT_00120258) = (ushort)bVar1 << 8;
        iVar4 = sStack_6 * 0x10 + DAT_00120258;
        iVar2 = sStack_8 * 2;
        *(ushort *)(iVar4 + iVar2 + 0x800) = ~((ushort)bVar1 << 8);
        bVar1 = s_<fnn_b<_0011ddc0[(int)sStack_8 + sStack_6 * 8];
        *(ushort *)(iVar4 + iVar2 + 0x1000) = (ushort)bVar1 << 8;
        *(ushort *)(iVar2 + iVar4 + 0x1800) = ~((ushort)bVar1 << 8);
      }
    }
    thunk_FUN_0012a0d0(&DAT_0012025c,4,8,8);
    uVar3 = 1;
  }
  return uVar3;
}



/* ===== thunk_FUN_0012a01c @ 00102ae4 (size 6) ===== */

void thunk_FUN_0012a01c(void)

{
  (**(code **)(GfxBase + -0xc0))();    /* = GfxBase.LoadRGB4() */
  return;
}



/* ===== thunk_FUN_0011a534 @ 00102aea (size 6) ===== */

int thunk_FUN_0011a534(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b154(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012b03c,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_001291d0 @ 00102af0 (size 6) ===== */

void thunk_FUN_001291d0(void)

{
  (**(code **)(SysBase + -0x234))();    /* = SysBase.ObtainSemaphore() */
  return;
}



/* ===== thunk_FUN_0012b1b0 @ 00102af6 (size 6) ===== */

void thunk_FUN_0012b1b0(void)

{
  (**(code **)(IntuitionBase + -0x10e))();    /* = IntuitionBase.SetPointer() */
  return;
}



/* ===== thunk_FUN_0011a4e0 @ 00102afc (size 6) ===== */

int thunk_FUN_0011a4e0(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b140(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(&LAB_0011a970,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_00114050 @ 00102b02 (size 6) ===== */

bool thunk_FUN_00114050(undefined4 param_1)

{
  DAT_00120154 = DAT_00120142;
  DAT_0012015a = 5;
  DAT_0012015c = param_1;
  DAT_00120160 = 0;
  DAT_00120164 = 0;
  thunk_FUN_001290f4(DAT_0012013e,&DAT_00120146);
  thunk_FUN_00129134(DAT_00120142);
  thunk_FUN_0012910c(DAT_00120142);
  return DAT_0012015b == '\0';
}



/* ===== thunk_FUN_0011a0b0 @ 00102b08 (size 6) ===== */

char thunk_FUN_0011a0b0(void)

{
  int *piVar1;
  undefined4 uStack_8;
  
  uStack_8 = (int *)PTR_DAT_0011ff1c;
  while ((*(char *)((int)uStack_8 + 9) == DAT_0011ff2a &&
         (piVar1 = (int *)*uStack_8, piVar1 != (int *)0x0))) {
    FUN_0011a054(uStack_8);
    uStack_8 = piVar1;
  }
  DAT_0011ff2a = DAT_0011ff2a + -1;
  return DAT_0011ff2a;
}



/* ===== thunk_FUN_0011a00a @ 00102b0e (size 6) ===== */

char thunk_FUN_0011a00a(void)

{
  undefined4 uStack_8;
  
  uStack_8 = (int *)PTR_DAT_0011ff1c;
  while ((DAT_0011ff2a == *(char *)((int)uStack_8 + 9) && ((int *)*uStack_8 != (int *)0x0))) {
    *(char *)((int)uStack_8 + 9) = *(char *)((int)uStack_8 + 9) + -1;
    uStack_8 = (int *)*uStack_8;
  }
  DAT_0011ff2a = DAT_0011ff2a + -1;
  return DAT_0011ff2a;
}



/* ===== thunk_FUN_0011a75c @ 00102b14 (size 6) ===== */

int thunk_FUN_0011a75c(undefined4 param_1,char param_2)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00125000(param_1,(int)(short)param_2);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(&LAB_0011a910,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_0011a868 @ 00102b1a (size 6) ===== */

int thunk_FUN_0011a868(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_001280d0(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(&LAB_0011a928,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_00101638 @ 00102b20 (size 6) ===== */

undefined8 thunk_FUN_00101638(undefined4 *param_1,int param_2)

{
  undefined4 uVar1;
  
  if (param_2 == 0) {
    param_2 = 1;
  }
  uVar1 = param_1[1];
  *(undefined4 *)param_1[0xe] = *param_1;
  return CONCAT44(param_2,uVar1);
}



/* ===== thunk_FUN_0012b050 @ 00102b26 (size 6) ===== */

void thunk_FUN_0012b050(void)

{
  (**(code **)(IntuitionBase + -0x66))();    /* = IntuitionBase.DoubleClick() */
  return;
}



/* ===== thunk_FUN_0011a11e @ 00102b2c (size 6) ===== */

void thunk_FUN_0011a11e(undefined4 param_1)

{
  FUN_0011a0f0();
  thunk_FUN_00100240(param_1);
  return;
}



/* ===== thunk_FUN_0011a238 @ 00102b32 (size 6) ===== */

void thunk_FUN_0011a238(int param_1)

{
  int iVar1;
  undefined4 uVar2;
  
  iVar1 = param_1 + -0x20;
  uVar2 = *(undefined4 *)(param_1 + -0xe);
  thunk_FUN_00129068(iVar1,uVar2,iVar1);
  thunk_FUN_00129038(iVar1,uVar2);
  return;
}



/* ===== thunk_FUN_0011a000 @ 00102b38 (size 6) ===== */

char thunk_FUN_0011a000(void)

{
  DAT_0011ff2a = DAT_0011ff2a + '\x01';
  return DAT_0011ff2a;
}



/* ===== thunk_FUN_0012b10c @ 00102b3e (size 6) ===== */

void thunk_FUN_0012b10c(void)

{
  (**(code **)(IntuitionBase + -0xba))();    /* = IntuitionBase.OnGadget() */
  return;
}



/* ===== thunk_FUN_001291e4 @ 00102b44 (size 6) ===== */

void thunk_FUN_001291e4(void)

{
  (**(code **)(SysBase + -0x23a))();    /* = SysBase.ReleaseSemaphore() */
  return;
}



/* ===== thunk_FUN_00101674 @ 00102b4a (size 6) ===== */

char * thunk_FUN_00101674(char *param_1,char *param_2)

{
  char cVar1;
  char *pcVar2;
  
  pcVar2 = param_1;
  do {
    cVar1 = *param_2;
    *pcVar2 = cVar1;
    param_2 = param_2 + 1;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  return param_1;
}



/* ===== thunk_FUN_0012b0d8 @ 00102b50 (size 6) ===== */

void thunk_FUN_0012b0d8(void)

{
  (**(code **)(IntuitionBase + -0xae))();    /* = IntuitionBase.OffGadget() */
  return;
}



/* ===== FUN_00103000 @ 00103000 (size 36) ===== */

void FUN_00103000(void)

{
  thunk_FUN_0012a068(DAT_001201c0,4,(int)DAT_001201f0,0xb,DAT_001201f0 + 7);
  return;
}



/* ===== thunk_FUN_0012a068 @ 001037c6 (size 6) ===== */

void thunk_FUN_0012a068(void)

{
  (**(code **)(GfxBase + -0x132))();    /* = GfxBase.RectFill() */
  return;
}



/* ===== FUN_00104000 @ 00104000 (size 304) ===== */

undefined4 FUN_00104000(void)

{
  undefined4 uVar1;
  int iVar2;
  bool bVar3;
  int iVar4;
  
  DAT_0011d702 = DAT_001200f8;
  DAT_00120254 = thunk_FUN_0011a534(&DAT_0011d6e4);
  if (DAT_00120254 == 0) {
    uVar1 = 0;
  }
  else {
    thunk_FUN_0012b088(*(undefined4 *)(DAT_00120254 + 0x32),&DAT_0011d740,0,0);
    PTR_s_Amiga_Compunet_Terminal_x_xx_0011d875_1_0011d8a0[0x18] = 0x32;
    PTR_s_Amiga_Compunet_Terminal_x_xx_0011d875_1_0011d8a0[0x1a] = 0x31;
    PTR_s_Amiga_Compunet_Terminal_x_xx_0011d875_1_0011d8a0[0x1b] = 0x20;
    thunk_FUN_0012b168(*(undefined4 *)(DAT_00120254 + 0x32),&DAT_0011d894,0,0);
    thunk_FUN_0012b06c(*(undefined4 *)(DAT_00120254 + 0x32),&DAT_0011d798,0,0);
    thunk_FUN_0012b234(DAT_00120254,&DAT_0011d714,0xffffffff,0xffffffff,0);
    thunk_FUN_0012b214(&DAT_0011d714,DAT_00120254,0,0xffffffff);
    do {
      thunk_FUN_00129134(*(undefined4 *)(DAT_00120254 + 0x56));
      bVar3 = false;
      iVar2 = thunk_FUN_0012910c(*(undefined4 *)(DAT_00120254 + 0x56));
      if (iVar2 != 0) {
        iVar4 = *(int *)(iVar2 + 0x1c);
        thunk_FUN_00129120(iVar2,iVar4,*(undefined4 *)(iVar2 + 0x14),iVar2);
        bVar3 = *(short *)(iVar4 + 0x26) == 1;
      }
    } while (!bVar3);
    thunk_FUN_0011a568(DAT_00120254);
    uVar1 = 1;
  }
  DAT_00120254 = 0;
  return uVar1;
}



/* ===== thunk_FUN_00129120 @ 00104130 (size 6) ===== */

void thunk_FUN_00129120(void)

{
  (**(code **)(SysBase + -0x17a))();    /* = SysBase.ReplyMsg() */
  return;
}



/* ===== thunk_FUN_0012b214 @ 00104136 (size 6) ===== */

void thunk_FUN_0012b214(void)

{
  (**(code **)(IntuitionBase + -0x1b0))();    /* = IntuitionBase.RefreshGList() */
  return;
}



/* ===== thunk_FUN_0012b234 @ 0010413c (size 6) ===== */

void thunk_FUN_0012b234(void)

{
  (**(code **)(IntuitionBase + -0x1b6))();    /* = IntuitionBase.AddGList() */
  return;
}



/* ===== thunk_FUN_0012b06c @ 00104142 (size 6) ===== */

void thunk_FUN_0012b06c(void)

{
  (**(code **)(IntuitionBase + -0x6c))();    /* = IntuitionBase.DrawBorder() */
  return;
}



/* ===== thunk_FUN_00129134 @ 00104148 (size 6) ===== */

void thunk_FUN_00129134(void)

{
  (**(code **)(SysBase + -0x180))();    /* = SysBase.WaitPort() */
  return;
}



/* ===== thunk_FUN_0012910c @ 0010414e (size 6) ===== */

void thunk_FUN_0012910c(void)

{
  (**(code **)(SysBase + -0x174))();    /* = SysBase.GetMsg() */
  return;
}



/* ===== thunk_FUN_0012b088 @ 00104154 (size 6) ===== */

void thunk_FUN_0012b088(void)

{
  (**(code **)(IntuitionBase + -0x72))();    /* = IntuitionBase.DrawImage() */
  return;
}



/* ===== thunk_FUN_0011a534 @ 0010415a (size 6) ===== */

int thunk_FUN_0011a534(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b154(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012b03c,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_0012b168 @ 00104160 (size 6) ===== */

void thunk_FUN_0012b168(void)

{
  (**(code **)(IntuitionBase + -0xd8))();    /* = IntuitionBase.PrintIText() */
  return;
}



/* ===== thunk_FUN_0011a568 @ 00104166 (size 6) ===== */

void thunk_FUN_0011a568(undefined4 param_1)

{
  thunk_FUN_0012b03c(param_1);
  FUN_0011a19c(thunk_FUN_0012b03c,param_1);
  return;
}



/* ===== FUN_00105000 @ 00105000 (size 16) ===== */

void FUN_00105000(int param_1)

{
  *(undefined1 *)(param_1 + 8) = 0;
  return;
}



/* ===== FUN_00105022 @ 00105022 (size 18) ===== */

void FUN_00105022(int param_1)

{
  *(undefined1 *)(param_1 + 8) = 2;
  return;
}



/* ===== FUN_0010506a @ 0010506a (size 18) ===== */

void FUN_0010506a(int param_1)

{
  *(undefined1 *)(param_1 + 8) = 6;
  return;
}



/* ===== FUN_00105180 @ 00105180 (size 26) ===== */

void FUN_00105180(int param_1)

{
  *(undefined2 *)(param_1 + 4) = 0;
  *(undefined2 *)(param_1 + 6) = 0;
  *(undefined2 *)(param_1 + 10) = 0;
  return;
}



/* ===== FUN_001051de @ 001051de (size 64) ===== */

void FUN_001051de(int param_1)

{
  *(short *)(param_1 + 6) = *(short *)(param_1 + 6) + 1;
  if (*(short *)(param_1 + 6) == 0x28) {
    *(undefined2 *)(param_1 + 6) = 0;
    if (*(short *)(param_1 + 4) < 0x17) {
      *(short *)(param_1 + 4) = *(short *)(param_1 + 4) + 1;
    }
  }
  *(undefined2 *)(param_1 + 10) = 0;
  return;
}



/* ===== FUN_0010521e @ 0010521e (size 50) ===== */

void FUN_0010521e(int param_1)

{
  *(short *)(param_1 + 6) = *(short *)(param_1 + 6) + -1;
  if (*(short *)(param_1 + 6) < 0) {
    *(undefined2 *)(param_1 + 6) = 0x27;
    if (0 < *(short *)(param_1 + 4)) {
      *(short *)(param_1 + 4) = *(short *)(param_1 + 4) + -1;
    }
  }
  *(undefined2 *)(param_1 + 10) = 0;
  return;
}



/* ===== FUN_00105250 @ 00105250 (size 46) ===== */

void FUN_00105250(int param_1)

{
  if ((*(short *)(param_1 + 10) == 0) && (*(short *)(param_1 + 4) < 0x17)) {
    *(short *)(param_1 + 4) = *(short *)(param_1 + 4) + 1;
  }
  *(undefined2 *)(param_1 + 6) = 0;
  *(undefined2 *)(param_1 + 10) = 0;
  *(undefined1 *)(param_1 + 9) = 0;
  return;
}



/* ===== FUN_0010544e @ 0010544e (size 110) ===== */

void FUN_0010544e(int param_1,int param_2,int param_3,int param_4,int param_5)

{
  int iVar1;
  undefined4 local_c;
  undefined4 local_8;
  
  for (local_8 = param_1; local_8 <= param_3; local_8 = local_8 + 1) {
    for (local_c = param_2; local_c <= param_4; local_c = local_c + 1) {
      iVar1 = thunk_FUN_00101604();
      *(undefined1 *)(local_c * 2 + iVar1 + param_5 + 0x10) = 0x20;
    }
  }
  thunk_FUN_001061e8(param_1,param_2,param_3,param_4,param_5);
  return;
}



/* ===== FUN_001054bc @ 001054bc (size 52) ===== */

void FUN_001054bc(int param_1)

{
  FUN_0010544e(0,0,0x17,0x27,param_1);
  *(undefined2 *)(param_1 + 4) = 0;
  *(undefined2 *)(param_1 + 6) = 0;
  *(undefined2 *)(param_1 + 10) = 0;
  return;
}



/* ===== FUN_001054f8 @ 001054f8 (size 358) ===== */

void FUN_001054f8(byte param_1,int param_2)

{
  short sVar1;
  short sVar2;
  char cVar3;
  byte bVar4;
  int iVar5;
  int iVar6;
  byte unaff_D7b;
  
  switch(param_1 >> 5) {
  case 0:
    (*(code *)(&PTR_LAB_0011d8a8)[(short)(ushort)param_1])(param_2);
    return;
  case 1:
    unaff_D7b = param_1;
    break;
  case 2:
    unaff_D7b = param_1 & 0x1f;
    break;
  case 3:
    unaff_D7b = param_1 & 0x1f | 0x40;
    break;
  case 4:
    (*(code *)(&PTR_LAB_0011d928)[param_1 & 0x7f])(param_2);
    return;
  case 5:
    unaff_D7b = param_1 & 0x1f | 0x60;
    break;
  case 6:
    unaff_D7b = param_1 & 0x7f;
    break;
  case 7:
    if (param_1 == 0xff) {
      unaff_D7b = 0x5e;
    }
    else {
      unaff_D7b = param_1 & 0x7f;
    }
  }
  bVar4 = *(byte *)(param_2 + 9) | unaff_D7b;
  sVar1 = *(short *)(param_2 + 4);
  sVar2 = *(short *)(param_2 + 6);
  iVar6 = sVar1 * 0x50;
  iVar5 = sVar2 * 2;
  cVar3 = *(char *)(iVar5 + iVar6 + param_2 + 0x10);
  *(byte *)(iVar5 + iVar6 + param_2 + 0x10) = bVar4;
  *(undefined1 *)(iVar5 + iVar6 + param_2 + 0x11) = *(undefined1 *)(param_2 + 8);
  if ((bVar4 != 0x20) || (cVar3 != ' ')) {
    thunk_FUN_00107000((int)sVar1,(int)sVar2,param_2);
  }
  FUN_001051de(param_2);
  *(short *)(param_2 + 10) = (short)(*(short *)(param_2 + 6) == 0);
  return;
}



/* ===== FUN_0010565e @ 0010565e (size 46) ===== */

void FUN_0010565e(char *param_1,undefined4 param_2)

{
  char cVar1;
  
  while( true ) {
    cVar1 = *param_1;
    param_1 = param_1 + 1;
    if (cVar1 == '\0') break;
    FUN_001054f8(cVar1,param_2);
  }
  return;
}



/* ===== FUN_0010568c @ 0010568c (size 30) ===== */

void FUN_0010568c(int param_1)

{
  *(undefined2 *)(param_1 + 0xc) = 1;
  *(undefined1 *)(param_1 + 9) = 0;
  FUN_001054bc(param_1);
  return;
}



/* ===== FUN_001056aa @ 001056aa (size 32) ===== */

void FUN_001056aa(undefined2 param_1,undefined2 param_2,int param_3)

{
  *(undefined2 *)(param_3 + 4) = param_1;
  *(undefined2 *)(param_3 + 6) = param_2;
  *(undefined2 *)(param_3 + 10) = 0;
  return;
}



/* ===== thunk_FUN_00107156 @ 001056cc (size 6) ===== */

void thunk_FUN_00107156(undefined4 param_1)

{
  undefined2 uStack_8;
  undefined2 uStack_6;
  
  FUN_001060f6();
  for (uStack_6 = 0; uStack_6 < 0x18; uStack_6 = uStack_6 + 1) {
    for (uStack_8 = 0; uStack_8 < 0x28; uStack_8 = uStack_8 + 1) {
      FUN_00107000((int)uStack_6,(int)uStack_8,param_1);
    }
  }
  FUN_0010617c(param_1);
  return;
}



/* ===== thunk_FUN_00101604 @ 001056d2 (size 6) ===== */

int thunk_FUN_00101604(void)

{
  uint in_D0;
  uint in_D1;
  
  return (uint)(ushort)((short)(in_D1 >> 0x10) * (short)in_D0 +
                       (short)(in_D0 >> 0x10) * (short)in_D1) * 0x10000 +
         (in_D0 & 0xffff) * (in_D1 & 0xffff);
}



/* ===== thunk_FUN_0012a0f0 @ 001056d8 (size 6) ===== */

void thunk_FUN_0012a0f0(void)

{
  (**(code **)(GfxBase + -0x18c))();    /* = GfxBase.ScrollRaster() */
  return;
}



/* ===== thunk_FUN_00107000 @ 001056de (size 6) ===== */

void thunk_FUN_00107000(short param_1,short param_2,int param_3)

{
  undefined2 uVar1;
  undefined1 uVar2;
  byte bVar3;
  byte bVar4;
  undefined4 in_D0;
  ushort uVar5;
  short sVar6;
  byte bVar7;
  undefined1 *puVar8;
  int iVar9;
  
  puVar8 = (undefined1 *)
           (param_2 * 2 + CONCAT22((short)((uint)in_D0 >> 0x10),param_1 * 0x50) + param_3 + 0x10);
  bVar3 = puVar8[1];
  bVar4 = *(byte *)(param_3 + 0xf);
  uVar1 = *(undefined2 *)(param_3 + 0xc);
  uVar2 = *puVar8;
  for (sVar6 = 0; sVar6 < 4; sVar6 = sVar6 + 1) {
    bVar7 = (byte)(1 << ((int)sVar6 & 0x3fU));
    uVar5 = (ushort)CONCAT21(uVar1,uVar2);
    if ((bVar7 & bVar3) == 0) {
      if ((bVar7 & bVar4) == 0) {
        iVar9 = DAT_00120258 + 0x200;
      }
      else {
        iVar9 = (short)(uVar5 ^ 0x80) * 0x10 + DAT_00120258;
      }
    }
    else if ((bVar7 & bVar4) == 0) {
      iVar9 = (short)uVar5 * 0x10 + DAT_00120258;
    }
    else {
      iVar9 = DAT_00120258 + 0xa00;
    }
    (&DAT_00120264)[sVar6] = iVar9;
  }
  if (DAT_0011d9a8 == 0) {
    (**(code **)(GfxBase + -0x25e))();    /* = GfxBase.BltBitMapRastPort() */
  }
  else {
    param_2 = param_2 + param_1 * 0x140;
    sVar6 = 3;
    do {
      puVar8 = *(undefined1 **)((int)&DAT_00120264 + (int)(short)(sVar6 << 2));
      iVar9 = *(int *)(&DAT_0012028c + (short)(sVar6 << 2));
      *(undefined1 *)(iVar9 + param_2) = *puVar8;
      *(undefined1 *)(iVar9 + 0x28 + (int)param_2) = puVar8[2];
      *(undefined1 *)(iVar9 + 0x50 + (int)param_2) = puVar8[4];
      *(undefined1 *)(iVar9 + 0x78 + (int)param_2) = puVar8[6];
      *(undefined1 *)(iVar9 + 0xa0 + (int)param_2) = puVar8[8];
      *(undefined1 *)(iVar9 + 200 + (int)param_2) = puVar8[10];
      *(undefined1 *)(iVar9 + 0xf0 + (int)param_2) = puVar8[0xc];
      *(undefined1 *)(iVar9 + 0x118 + (int)param_2) = puVar8[0xe];
      sVar6 = sVar6 + -1;
    } while (sVar6 != -1);
  }
  return;
}



/* ===== thunk_FUN_001061e8 @ 001056e4 (size 6) ===== */

void thunk_FUN_001061e8(int param_1,int param_2,short param_3,short param_4,int *param_5)

{
  DAT_0011d9bb = *(undefined1 *)((int)param_5 + 0xf);
  DAT_0011d9b0 = ((param_4 - (short)param_2) + 1) * 8;
  DAT_0011d9b2 = ((param_3 - (short)param_1) + 1) * 8;
  if (DAT_0011d9a8 == 0) {
    thunk_FUN_0012b088(*(undefined4 *)(*param_5 + 0x32),&DAT_0011d9ac,param_2 * 8 + 4,
                       param_1 * 8 + 10);
  }
  else {
    thunk_FUN_0012b088(&DAT_001202ac,&DAT_0011d9ac,param_2 << 3,param_1 << 3);
  }
  return;
}



/* ===== thunk_FUN_0012a0a0 @ 001056ea (size 6) ===== */

void thunk_FUN_0012a0a0(void)

{
  (**(code **)(GfxBase + -0x15c))();    /* = GfxBase.SetBPen() */
  return;
}



/* ===== FUN_00106000 @ 00106000 (size 246) ===== */
/* strings: <fnn`b< */

undefined4 FUN_00106000(void)

{
  byte bVar1;
  int iVar2;
  undefined4 uVar3;
  int iVar4;
  short local_8;
  short local_6;
  
  DAT_00120258 = thunk_FUN_0011a1ee(0x2000,2);
  if (DAT_00120258 == 0) {
    uVar3 = 0;
  }
  else {
    for (local_6 = 0; local_6 < 0x80; local_6 = local_6 + 1) {
      for (local_8 = 0; local_8 < 8; local_8 = local_8 + 1) {
        bVar1 = s_<fnn_b<_0011d9c0[(int)local_8 + local_6 * 8];
        *(ushort *)(local_8 * 2 + local_6 * 0x10 + DAT_00120258) = (ushort)bVar1 << 8;
        iVar4 = local_6 * 0x10 + DAT_00120258;
        iVar2 = local_8 * 2;
        *(ushort *)(iVar4 + iVar2 + 0x800) = ~((ushort)bVar1 << 8);
        bVar1 = s_<fnn_b<_0011ddc0[(int)local_8 + local_6 * 8];
        *(ushort *)(iVar4 + iVar2 + 0x1000) = (ushort)bVar1 << 8;
        *(ushort *)(iVar2 + iVar4 + 0x1800) = ~((ushort)bVar1 << 8);
      }
    }
    thunk_FUN_0012a0d0(&DAT_0012025c,4,8,8);
    uVar3 = 1;
  }
  return uVar3;
}



/* ===== FUN_001060f6 @ 001060f6 (size 134) ===== */

void FUN_001060f6(void)

{
  int iVar1;
  int local_8;
  
  thunk_FUN_0012a038(&DAT_001202ac);
  thunk_FUN_0012a0d0(&DAT_00120284,4,0x140,0xc0);
  DAT_001202b0 = &DAT_00120284;
  thunk_FUN_0011a000();
  local_8 = 0;
  while( true ) {
    if (3 < local_8) {
      thunk_FUN_0011a00a();
      DAT_0011d9a8 = 1;
      return;
    }
    iVar1 = thunk_FUN_0011a1ee(0x1e00,2);
    *(int *)(&DAT_0012028c + local_8 * 4) = iVar1;
    if (iVar1 == 0) break;
    local_8 = local_8 + 1;
  }
  thunk_FUN_0011a0b0();
  DAT_0011d9a8 = 0;
  return;
}



/* ===== FUN_0010617c @ 0010617c (size 108) ===== */

void FUN_0010617c(int *param_1)

{
  int local_8;
  
  if (DAT_0011d9a8 != 0) {
    thunk_FUN_0012a110(&DAT_00120284,0,0,*(undefined4 *)(*param_1 + 0x32),4,10,0x140,0xc0,0xc0);
    for (local_8 = 0; local_8 < 4; local_8 = local_8 + 1) {
      thunk_FUN_0011a238(*(undefined4 *)(&DAT_0012028c + local_8 * 4));
    }
    DAT_0011d9a8 = 0;
  }
  return;
}



/* ===== FUN_001061e8 @ 001061e8 (size 142) ===== */

void FUN_001061e8(int param_1,int param_2,short param_3,short param_4,int *param_5)

{
  DAT_0011d9bb = *(undefined1 *)((int)param_5 + 0xf);
  DAT_0011d9b0 = ((param_4 - (short)param_2) + 1) * 8;
  DAT_0011d9b2 = ((param_3 - (short)param_1) + 1) * 8;
  if (DAT_0011d9a8 == 0) {
    thunk_FUN_0012b088(*(undefined4 *)(*param_5 + 0x32),&DAT_0011d9ac,param_2 * 8 + 4,
                       param_1 * 8 + 10);
  }
  else {
    thunk_FUN_0012b088(&DAT_001202ac,&DAT_0011d9ac,param_2 << 3,param_1 << 3);
  }
  return;
}



/* ===== thunk_FUN_0012a038 @ 00106278 (size 6) ===== */

void thunk_FUN_0012a038(void)

{
  (**(code **)(GfxBase + -0xc6))();    /* = GfxBase.InitRastPort() */
  return;
}



/* ===== thunk_FUN_0012a0d0 @ 0010627e (size 6) ===== */

void thunk_FUN_0012a0d0(void)

{
  (**(code **)(GfxBase + -0x186))();    /* = GfxBase.InitBitMap() */
  return;
}



/* ===== thunk_FUN_0012a110 @ 00106284 (size 6) ===== */

void thunk_FUN_0012a110(void)

{
  (**(code **)(GfxBase + -0x25e))();    /* = GfxBase.BltBitMapRastPort() */
  return;
}



/* ===== thunk_FUN_0012b088 @ 0010628a (size 6) ===== */

void thunk_FUN_0012b088(void)

{
  (**(code **)(IntuitionBase + -0x72))();    /* = IntuitionBase.DrawImage() */
  return;
}



/* ===== thunk_FUN_0011a0b0 @ 00106290 (size 6) ===== */

char thunk_FUN_0011a0b0(void)

{
  int *piVar1;
  undefined4 uStack_8;
  
  uStack_8 = (int *)PTR_DAT_0011ff1c;
  while ((*(char *)((int)uStack_8 + 9) == DAT_0011ff2a &&
         (piVar1 = (int *)*uStack_8, piVar1 != (int *)0x0))) {
    FUN_0011a054(uStack_8);
    uStack_8 = piVar1;
  }
  DAT_0011ff2a = DAT_0011ff2a + -1;
  return DAT_0011ff2a;
}



/* ===== thunk_FUN_0011a00a @ 00106296 (size 6) ===== */

char thunk_FUN_0011a00a(void)

{
  undefined4 uStack_8;
  
  uStack_8 = (int *)PTR_DAT_0011ff1c;
  while ((DAT_0011ff2a == *(char *)((int)uStack_8 + 9) && ((int *)*uStack_8 != (int *)0x0))) {
    *(char *)((int)uStack_8 + 9) = *(char *)((int)uStack_8 + 9) + -1;
    uStack_8 = (int *)*uStack_8;
  }
  DAT_0011ff2a = DAT_0011ff2a + -1;
  return DAT_0011ff2a;
}



/* ===== thunk_FUN_0011a1ee @ 0010629c (size 6) ===== */

int thunk_FUN_0011a1ee(int param_1,undefined4 param_2)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00129020(param_1 + 0x20,param_2);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a132(iVar1,0,param_1 + 0x20,0);
    iVar1 = iVar1 + 0x20;
  }
  return iVar1;
}



/* ===== thunk_FUN_0011a238 @ 001062a2 (size 6) ===== */

void thunk_FUN_0011a238(int param_1)

{
  int iVar1;
  undefined4 uVar2;
  
  iVar1 = param_1 + -0x20;
  uVar2 = *(undefined4 *)(param_1 + -0xe);
  thunk_FUN_00129068(iVar1,uVar2,iVar1);
  thunk_FUN_00129038(iVar1,uVar2);
  return;
}



/* ===== thunk_FUN_0011a000 @ 001062a8 (size 6) ===== */

char thunk_FUN_0011a000(void)

{
  DAT_0011ff2a = DAT_0011ff2a + '\x01';
  return DAT_0011ff2a;
}



/* ===== FUN_00107000 @ 00107000 (size 342) ===== */

void FUN_00107000(short param_1,short param_2,int param_3)

{
  undefined2 uVar1;
  undefined1 uVar2;
  byte bVar3;
  byte bVar4;
  undefined4 in_D0;
  ushort uVar5;
  short sVar6;
  byte bVar7;
  undefined1 *puVar8;
  int iVar9;
  
  puVar8 = (undefined1 *)
           (param_2 * 2 + CONCAT22((short)((uint)in_D0 >> 0x10),param_1 * 0x50) + param_3 + 0x10);
  bVar3 = puVar8[1];
  bVar4 = *(byte *)(param_3 + 0xf);
  uVar1 = *(undefined2 *)(param_3 + 0xc);
  uVar2 = *puVar8;
  for (sVar6 = 0; sVar6 < 4; sVar6 = sVar6 + 1) {
    bVar7 = (byte)(1 << ((int)sVar6 & 0x3fU));
    uVar5 = (ushort)CONCAT21(uVar1,uVar2);
    if ((bVar7 & bVar3) == 0) {
      if ((bVar7 & bVar4) == 0) {
        iVar9 = DAT_00120258 + 0x200;
      }
      else {
        iVar9 = (short)(uVar5 ^ 0x80) * 0x10 + DAT_00120258;
      }
    }
    else if ((bVar7 & bVar4) == 0) {
      iVar9 = (short)uVar5 * 0x10 + DAT_00120258;
    }
    else {
      iVar9 = DAT_00120258 + 0xa00;
    }
    (&DAT_00120264)[sVar6] = iVar9;
  }
  if (DAT_0011d9a8 == 0) {
    (**(code **)(GfxBase + -0x25e))();    /* = GfxBase.BltBitMapRastPort() */
  }
  else {
    param_2 = param_2 + param_1 * 0x140;
    sVar6 = 3;
    do {
      puVar8 = *(undefined1 **)((int)&DAT_00120264 + (int)(short)(sVar6 << 2));
      iVar9 = *(int *)(&DAT_0012028c + (short)(sVar6 << 2));
      *(undefined1 *)(iVar9 + param_2) = *puVar8;
      *(undefined1 *)(iVar9 + 0x28 + (int)param_2) = puVar8[2];
      *(undefined1 *)(iVar9 + 0x50 + (int)param_2) = puVar8[4];
      *(undefined1 *)(iVar9 + 0x78 + (int)param_2) = puVar8[6];
      *(undefined1 *)(iVar9 + 0xa0 + (int)param_2) = puVar8[8];
      *(undefined1 *)(iVar9 + 200 + (int)param_2) = puVar8[10];
      *(undefined1 *)(iVar9 + 0xf0 + (int)param_2) = puVar8[0xc];
      *(undefined1 *)(iVar9 + 0x118 + (int)param_2) = puVar8[0xe];
      sVar6 = sVar6 + -1;
    } while (sVar6 != -1);
  }
  return;
}



/* ===== FUN_00107156 @ 00107156 (size 88) ===== */

void FUN_00107156(undefined4 param_1)

{
  undefined2 local_8;
  undefined2 local_6;
  
  FUN_001060f6();
  for (local_6 = 0; local_6 < 0x18; local_6 = local_6 + 1) {
    for (local_8 = 0; local_8 < 0x28; local_8 = local_8 + 1) {
      FUN_00107000((int)local_6,(int)local_8,param_1);
    }
  }
  FUN_0010617c(param_1);
  return;
}



/* ===== FUN_00108000 @ 00108000 (size 12) ===== */

undefined1 FUN_00108000(void)

{
  undefined1 *puVar1;
  
  puVar1 = DAT_001203a8;
  DAT_001203a8 = DAT_001203a8 + 1;
  return *puVar1;
}



/* ===== FUN_0010800c @ 0010800c (size 122) ===== */

undefined1 FUN_0010800c(void)

{
  undefined1 *puVar1;
  undefined1 local_6;
  undefined1 uStack_5;
  
  if (DAT_001203a0 < DAT_001203a4) {
    puVar1 = &DAT_00120310 + DAT_001203a0;
    DAT_001203a0 = DAT_001203a0 + 1;
    local_6 = *puVar1;
  }
  else if (DAT_001203ac == '\0') {
    thunk_FUN_0011967c(&DAT_00120310,0x8f,&DAT_001203ac,&uStack_5,&DAT_001203a4);
    DAT_001203a0 = 1;
    local_6 = DAT_00120310;
  }
  else {
    local_6 = 0;
  }
  if (DAT_001203ae != (undefined1 *)0x0) {
    *DAT_001203ae = local_6;
    DAT_001203ae = DAT_001203ae + 1;
  }
  return local_6;
}



/* ===== FUN_00108086 @ 00108086 (size 84) ===== */

char FUN_00108086(void)

{
  if (DAT_001203bb == '\0') {
    DAT_001203ba = (*DAT_001203b6)();
    if (DAT_001203ba == '\x06') {
      DAT_001203ba = ' ';
      DAT_001203bb = (*DAT_001203b6)();
    }
    else if (DAT_001203ba == '\a') {
      DAT_001203ba = (*DAT_001203b6)();
      DAT_001203bb = (*DAT_001203b6)();
    }
  }
  else {
    DAT_001203bb = DAT_001203bb + -1;
  }
  return DAT_001203ba;
}



/* ===== FUN_001080da @ 001080da (size 176) ===== */

void FUN_001080da(undefined4 param_1,int param_2)

{
  uint uVar1;
  char cVar2;
  
  thunk_FUN_001060f6();
  DAT_001203a8 = param_1;
  DAT_001203b6 = FUN_00108000;
  FUN_00108000();
  uVar1 = FUN_00108000();
  *(undefined *)(param_2 + 0xe) = (&DAT_0011e1c0)[uVar1 & 0xf];
  uVar1 = FUN_00108000();
  *(undefined *)(param_2 + 0xf) = (&DAT_0011e1c0)[uVar1 & 0xf];
  thunk_FUN_0010568c(param_2);
  cVar2 = FUN_00108000();
  *(ushort *)(param_2 + 0xc) = (ushort)(cVar2 == '\x0e');
  DAT_001203bb = 0;
  while (cVar2 = FUN_00108086(), cVar2 != '\0') {
    thunk_FUN_001054f8(cVar2,param_2);
  }
  thunk_FUN_0010617c(param_2);
  return;
}



/* ===== FUN_0010818a @ 0010818a (size 202) ===== */

undefined1 * FUN_0010818a(int param_1,undefined1 *param_2)

{
  uint uVar1;
  char cVar2;
  
  DAT_001203b6 = FUN_0010800c;
  DAT_001203a0 = 0;
  DAT_001203a4 = 0;
  DAT_001203ac = 0;
  DAT_001203ae = param_2;
  uVar1 = FUN_0010800c();
  DAT_001203b2 = uVar1 & 0x80;
  *param_2 = 0;
  uVar1 = FUN_0010800c();
  *(undefined *)(param_1 + 0xe) = (&DAT_0011e1c0)[uVar1 & 0xf];
  uVar1 = FUN_0010800c();
  *(undefined *)(param_1 + 0xf) = (&DAT_0011e1c0)[uVar1 & 0xf];
  thunk_FUN_0010568c(param_1);
  cVar2 = FUN_0010800c();
  *(ushort *)(param_1 + 0xc) = (ushort)(cVar2 == '\x0e');
  DAT_001203bb = 0;
  while (cVar2 = FUN_00108086(), cVar2 != '\0') {
    thunk_FUN_001054f8(cVar2,param_1);
  }
  return DAT_001203ae;
}



/* ===== FUN_00108254 @ 00108254 (size 42) ===== */

void FUN_00108254(int param_1)

{
  thunk_FUN_0011956a(param_1 + 0x16,*(undefined4 *)(param_1 + 0x12),1,0x22);
  return;
}



/* ===== thunk_FUN_0010568c @ 00108280 (size 6) ===== */

void thunk_FUN_0010568c(int param_1)

{
  *(undefined2 *)(param_1 + 0xc) = 1;
  *(undefined1 *)(param_1 + 9) = 0;
  FUN_001054bc(param_1);
  return;
}



/* ===== thunk_FUN_001060f6 @ 00108286 (size 6) ===== */

void thunk_FUN_001060f6(void)

{
  int iVar1;
  int iStack_8;
  
  thunk_FUN_0012a038(&DAT_001202ac);
  thunk_FUN_0012a0d0(&DAT_00120284,4,0x140,0xc0);
  DAT_001202b0 = &DAT_00120284;
  thunk_FUN_0011a000();
  iStack_8 = 0;
  while( true ) {
    if (3 < iStack_8) {
      thunk_FUN_0011a00a();
      DAT_0011d9a8 = 1;
      return;
    }
    iVar1 = thunk_FUN_0011a1ee(0x1e00,2);
    *(int *)(&DAT_0012028c + iStack_8 * 4) = iVar1;
    if (iVar1 == 0) break;
    iStack_8 = iStack_8 + 1;
  }
  thunk_FUN_0011a0b0();
  DAT_0011d9a8 = 0;
  return;
}



/* ===== thunk_FUN_0011967c @ 0010828c (size 6) ===== */

undefined4
thunk_FUN_0011967c(undefined4 param_1,undefined4 param_2,undefined1 *param_3,undefined1 *param_4,
                  undefined4 *param_5)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b8 + 0x28) = param_1;
  *(undefined4 *)(DAT_001230b8 + 0x24) = param_2;
  *(undefined2 *)(DAT_001230b8 + 0x1c) = 2;
  thunk_FUN_001291a4(DAT_001230b8);
  uVar2 = DAT_00120104 | DAT_001230c6 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c6 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230ac), iVar4 == 0));
  *param_4 = *(undefined1 *)(DAT_001230b8 + 0x2c);
  *param_3 = *(undefined1 *)(DAT_001230b8 + 0x2d);
  *param_5 = *(undefined4 *)(DAT_001230b8 + 0x20);
  cVar1 = *(char *)(DAT_001230b8 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011fed6);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 1;
    }
    if (cVar1 == '\0') {
      return 1;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011fee4);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 1;
}



/* ===== thunk_FUN_0010617c @ 00108292 (size 6) ===== */

void thunk_FUN_0010617c(int *param_1)

{
  int iStack_8;
  
  if (DAT_0011d9a8 != 0) {
    thunk_FUN_0012a110(&DAT_00120284,0,0,*(undefined4 *)(*param_1 + 0x32),4,10,0x140,0xc0,0xc0);
    for (iStack_8 = 0; iStack_8 < 4; iStack_8 = iStack_8 + 1) {
      thunk_FUN_0011a238(*(undefined4 *)(&DAT_0012028c + iStack_8 * 4));
    }
    DAT_0011d9a8 = 0;
  }
  return;
}



/* ===== thunk_FUN_0011956a @ 00108298 (size 6) ===== */

undefined4
thunk_FUN_0011956a(undefined4 param_1,undefined4 param_2,undefined1 param_3,undefined1 param_4)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b4 + 0x28) = param_1;
  *(undefined4 *)(DAT_001230b4 + 0x24) = param_2;
  *(undefined1 *)(DAT_001230b4 + 0x2c) = param_4;
  *(undefined1 *)(DAT_001230b4 + 0x2d) = param_3;
  *(undefined2 *)(DAT_001230b4 + 0x1c) = 3;
  thunk_FUN_001291a4(DAT_001230b4);
  uVar2 = DAT_00120104 | DAT_001230c2 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c2 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230b0), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b4 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011feba);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 1;
    }
    if (cVar1 == '\0') {
      return 1;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011fec8);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 1;
}



/* ===== thunk_FUN_001054f8 @ 0010829e (size 6) ===== */

void thunk_FUN_001054f8(byte param_1,int param_2)

{
  short sVar1;
  short sVar2;
  char cVar3;
  byte bVar4;
  int iVar5;
  int iVar6;
  byte unaff_D7b;
  
  switch(param_1 >> 5) {
  case 0:
    (*(code *)(&PTR_LAB_0011d8a8)[(short)(ushort)param_1])(param_2);
    return;
  case 1:
    unaff_D7b = param_1;
    break;
  case 2:
    unaff_D7b = param_1 & 0x1f;
    break;
  case 3:
    unaff_D7b = param_1 & 0x1f | 0x40;
    break;
  case 4:
    (*(code *)(&PTR_LAB_0011d928)[param_1 & 0x7f])(param_2);
    return;
  case 5:
    unaff_D7b = param_1 & 0x1f | 0x60;
    break;
  case 6:
    unaff_D7b = param_1 & 0x7f;
    break;
  case 7:
    if (param_1 == 0xff) {
      unaff_D7b = 0x5e;
    }
    else {
      unaff_D7b = param_1 & 0x7f;
    }
  }
  bVar4 = *(byte *)(param_2 + 9) | unaff_D7b;
  sVar1 = *(short *)(param_2 + 4);
  sVar2 = *(short *)(param_2 + 6);
  iVar6 = sVar1 * 0x50;
  iVar5 = sVar2 * 2;
  cVar3 = *(char *)(iVar5 + iVar6 + param_2 + 0x10);
  *(byte *)(iVar5 + iVar6 + param_2 + 0x10) = bVar4;
  *(undefined1 *)(iVar5 + iVar6 + param_2 + 0x11) = *(undefined1 *)(param_2 + 8);
  if ((bVar4 != 0x20) || (cVar3 != ' ')) {
    thunk_FUN_00107000((int)sVar1,(int)sVar2,param_2);
  }
  FUN_001051de(param_2);
  *(short *)(param_2 + 10) = (short)(*(short *)(param_2 + 6) == 0);
  return;
}



/* ===== FUN_00109000 @ 00109000 (size 498) ===== */

void FUN_00109000(int param_1)

{
  int iVar1;
  int *local_e;
  short local_6;
  
  local_e = (int *)0x0;
  for (local_6 = 0; local_6 < 0xb; local_6 = local_6 + 1) {
    iVar1 = local_6 * 0x34 + param_1;
    *(int *)(iVar1 + 0xc7a) = (int)local_e;
    *(undefined2 *)(iVar1 + 0xc7e) = 0xc;
    *(short *)(iVar1 + 0xc80) = local_6 * 8 + 0x5a;
    *(undefined2 *)(iVar1 + 0xc82) = 0x130;
    *(undefined2 *)(iVar1 + 0xc84) = 8;
    *(undefined2 *)(iVar1 + 0xc86) = 3;
    *(undefined2 *)(iVar1 + 0xc88) = 0x102;
    *(undefined2 *)(iVar1 + 0xc8a) = 1;
    *(undefined4 *)(iVar1 + 0xc8c) = 0;
    *(undefined4 *)(iVar1 + 0xc90) = 0;
    *(undefined4 *)(iVar1 + 0xc94) = 0;
    *(undefined4 *)(iVar1 + 0xc98) = 0;
    *(undefined4 *)(iVar1 + 0xc9c) = 0;
    *(short *)(iVar1 + 0xca0) = local_6;
    *(undefined4 *)(iVar1 + 0xca2) = 0;
    *(code **)(iVar1 + 0xca6) = FUN_0010935a;
    *(int *)(iVar1 + 0xcaa) = param_1;
    local_e = (int *)(iVar1 + 0xc7a);
  }
  for (local_6 = 0; local_6 < 5; local_6 = local_6 + 1) {
    iVar1 = local_6 * 0x34 + param_1;
    *(int *)(iVar1 + 0xeb6) = (int)local_e;
    *(short *)(iVar1 + 0xeba) = local_6 * 0x40 + 7;
    *(undefined2 *)(iVar1 + 0xebc) = 0xcb;
    *(undefined2 *)(iVar1 + 0xebe) = 0x3c;
    *(undefined2 *)(iVar1 + 0xec0) = 0x10;
    *(undefined2 *)(iVar1 + 0xec2) = 0x107;
    *(undefined2 *)(iVar1 + 0xec4) = 0x102;
    *(undefined2 *)(iVar1 + 0xec6) = 1;
    *(undefined **)(iVar1 + 0xec8) = &DAT_0011e212;
    *(undefined4 *)(iVar1 + 0xecc) = 0;
    *(undefined **)(iVar1 + 0xed0) = &DAT_0011e2da + local_6 * 0x14;
    *(undefined4 *)(iVar1 + 0xed4) = 0;
    *(undefined4 *)(iVar1 + 0xed8) = 0;
    *(short *)(iVar1 + 0xedc) = local_6;
    *(undefined4 *)(iVar1 + 0xede) = 0;
    *(undefined4 *)(iVar1 + 0xee2) = *(undefined4 *)(&DAT_0011e33e + local_6 * 4);
    *(int *)(iVar1 + 0xee6) = param_1;
    local_e = (int *)(iVar1 + 0xeb6);
  }
  for (local_6 = 0; local_6 < 2; local_6 = local_6 + 1) {
    iVar1 = local_6 * 0x34 + param_1;
    *(int *)(iVar1 + 0xfba) = (int)local_e;
    *(short *)(iVar1 + 0xfbe) = local_6 * 0x20 + 0xfc;
    *(undefined2 *)(iVar1 + 0xfc0) = 0xb2;
    *(undefined2 *)(iVar1 + 0xfc2) = 0x20;
    *(undefined2 *)(iVar1 + 0xfc4) = 8;
    *(undefined2 *)(iVar1 + 0xfc6) = 3;
    *(undefined2 *)(iVar1 + 0xfc8) = 0x102;
    *(undefined2 *)(iVar1 + 0xfca) = 1;
    *(undefined4 *)(iVar1 + 0xfcc) = 0;
    *(undefined4 *)(iVar1 + 0xfd0) = 0;
    *(undefined4 *)(iVar1 + 0xfd4) = 0;
    *(undefined4 *)(iVar1 + 0xfd8) = 0;
    *(undefined4 *)(iVar1 + 0xfdc) = 0;
    *(short *)(iVar1 + 0xfe0) = local_6;
    *(undefined4 *)(iVar1 + 0xfe2) = 0;
    *(undefined **)(iVar1 + 0xfe6) = (&PTR_LAB_0011e352)[local_6];
    *(int *)(iVar1 + 0xfea) = param_1;
    local_e = (int *)(iVar1 + 0xfba);
  }
  return;
}



/* ===== FUN_001091f2 @ 001091f2 (size 180) ===== */

void FUN_001091f2(undefined4 *param_1)

{
  undefined2 uVar1;
  short local_6;
  
  uVar1 = thunk_FUN_0012b254(*param_1,(int)param_1 + 0xf86,5);
  for (local_6 = 0; local_6 < 5; local_6 = local_6 + 1) {
    param_1[local_6 * 0xd + 0x3b4] = &DAT_0011e376 + local_6 * 0x14;
    *(undefined4 *)((int)param_1 + local_6 * 0x34 + 0xee2) =
         *(undefined4 *)(&DAT_0011e3da + local_6 * 4);
  }
  thunk_FUN_0012b234(*param_1,(int)param_1 + 0xf86,uVar1,5,0);
  thunk_FUN_0012b214((int)param_1 + 0xf86,*param_1,0,5);
  return;
}



/* ===== FUN_0010935a @ 0010935a (size 454) ===== */

undefined4 FUN_0010935a(int param_1,int param_2)

{
  int *piVar1;
  short sVar2;
  short sVar3;
  undefined4 uVar4;
  
  sVar2 = *(short *)(param_1 + 0x26);
  piVar1 = *(int **)(param_1 + 0x30);
  if (*(short *)((int)piVar1 + 0xc76) <= sVar2) {
    return 0;
  }
  if ((param_2 == 0) || (DAT_0011d070 < 2)) goto switchD_0010939e_default;
  switch(DAT_0011d070) {
  case 2:
    goto LAB_001093b0;
  case 3:
LAB_001093b0:
    if (param_2 == 2) {
      uVar4 = FUN_0010963c((int)piVar1 + 0xf52,0);
      return uVar4;
    }
LAB_001093d0:
    if (param_2 == 1) {
      uVar4 = FUN_0010956c((int)piVar1 + 0xeb6,0);
      return uVar4;
    }
    break;
  case 4:
    break;
  case 5:
    if (param_2 == 2) {
      uVar4 = FUN_0010a484((int)piVar1 + 0xf52,0);
      return uVar4;
    }
    break;
  case 6:
    break;
  case 7:
    break;
  case 8:
    goto LAB_001093d0;
  }
switchD_0010939e_default:
  sVar3 = *(short *)(piVar1 + 0x31e);
  if (-1 < sVar3) {
    thunk_FUN_0012a0b8(*(undefined4 *)(*piVar1 + 0x32),2);
    thunk_FUN_0012a068(*(undefined4 *)(*piVar1 + 0x32),0xc,sVar3 * 8 + 0x5a,0xf3,sVar3 * 8 + 0x61);
    thunk_FUN_0012a068(*(undefined4 *)(*piVar1 + 0x32),0xfc,sVar3 * 8 + 0x5a,0x13b,sVar3 * 8 + 0x61)
    ;
  }
  *(short *)(piVar1 + 0x31e) = sVar2;
  thunk_FUN_0012a0b8(*(undefined4 *)(*piVar1 + 0x32),2);
  thunk_FUN_0012a068(*(undefined4 *)(*piVar1 + 0x32),0xc,sVar2 * 8 + 0x5a,0xf3,sVar2 * 8 + 0x61);
  thunk_FUN_0012a068(*(undefined4 *)(*piVar1 + 0x32),0xfc,sVar2 * 8 + 0x5a,0x13b,sVar2 * 8 + 0x61);
  return 1;
}



/* ===== FUN_00109520 @ 00109520 (size 76) ===== */

void FUN_00109520(int *param_1,short param_2)

{
  thunk_FUN_0012a0b8(*(undefined4 *)(*param_1 + 0x32),2);
  thunk_FUN_0012a068(*(undefined4 *)(*param_1 + 0x32),param_2 * 0x40 + 7,0xcb,param_2 * 0x40 + 0x42,
                     0xda);
  return;
}



/* ===== FUN_0010956c @ 0010956c (size 68) ===== */

undefined4 FUN_0010956c(int param_1)

{
  undefined4 uVar1;
  undefined4 uVar2;
  
  uVar1 = *(undefined4 *)(param_1 + 0x30);
  FUN_00109520(uVar1,*(undefined2 *)(param_1 + 0x26));
  uVar2 = FUN_0010a1e2();
  FUN_00109520(uVar1,*(undefined2 *)(param_1 + 0x26));
  return uVar2;
}



/* ===== FUN_0010963c @ 0010963c (size 70) ===== */

undefined4 FUN_0010963c(int param_1)

{
  undefined4 uVar1;
  undefined4 uVar2;
  
  uVar1 = *(undefined4 *)(param_1 + 0x30);
  FUN_00109520(uVar1,*(undefined2 *)(param_1 + 0x26));
  uVar2 = thunk_FUN_0010b730();
  FUN_00109520(uVar1,*(undefined2 *)(param_1 + 0x26));
  return uVar2;
}



/* ===== FUN_001096c8 @ 001096c8 (size 388) ===== */

void FUN_001096c8(int *param_1)

{
  short sVar1;
  short sVar2;
  short sVar3;
  int iVar4;
  short local_a;
  
  sVar1 = *(short *)(param_1 + 0x31d);
  sVar2 = *(short *)((int)param_1 + 0xc76);
  sVar3 = *(short *)(param_1 + 0x31e);
  thunk_FUN_0012a0b8(*(undefined4 *)(*param_1 + 0x32),2);
  iVar4 = sVar3 * 8;
  thunk_FUN_0012a068(*(undefined4 *)(*param_1 + 0x32),0xfc,iVar4 + 0x5a,0x13b,iVar4 + 0x61);
  thunk_FUN_001056aa(7,0x1f,param_1);
  thunk_FUN_0010506a(param_1);
  thunk_FUN_0010565e((int)param_1 + sVar1 * 9 + 0x7c8,param_1);
  thunk_FUN_001056aa(10,0x1f,param_1);
  thunk_FUN_00105022(param_1);
  thunk_FUN_0010565e((int)param_1 + sVar1 * 9 + 0x82e,param_1);
  thunk_FUN_0010506a(param_1);
  for (local_a = 1; local_a < sVar2; local_a = local_a + 1) {
    thunk_FUN_001056aa(local_a + 10,0x1f,param_1);
    thunk_FUN_0010565e((int)param_1 + sVar1 * 9 + local_a * 0x66 + 0x82e,param_1);
  }
  thunk_FUN_0012a0b8(*(undefined4 *)(*param_1 + 0x32),2);
  iVar4 = sVar3 * 8;
  thunk_FUN_0012a068(*(undefined4 *)(*param_1 + 0x32),0xfc,iVar4 + 0x5a,0x13b,iVar4 + 0x61);
  return;
}



/* ===== FUN_00109a5e @ 00109a5e (size 1924) ===== */

void FUN_00109a5e(undefined4 *param_1)

{
  undefined1 uVar1;
  char cVar2;
  short sVar3;
  undefined4 *puVar4;
  undefined4 *local_10;
  short local_c;
  short local_a;
  short local_8;
  byte local_6;
  byte local_5;
  
  DAT_001203b6 = &LAB_0010a5ac;
  DAT_001203a0 = 0;
  DAT_001203a4 = 0;
  DAT_001203ae = 0;
  DAT_001203ac = 0;
  DAT_001203bb = 0;
  local_5 = thunk_FUN_00108086();
  if (local_5 != '\0') {
    thunk_FUN_0010544e(0,0,5,0x27,param_1);
    thunk_FUN_00105180(param_1);
    do {
      thunk_FUN_001054f8(local_5,param_1);
      local_5 = thunk_FUN_00108086();
    } while (local_5 != '\0');
  }
  thunk_FUN_0010544e(10,1,0x14,0x1d,param_1);
  thunk_FUN_0010544e(10,0x1f,0x14,0x26,param_1);
  local_5 = thunk_FUN_00108086();
  if (local_5 != 0) {
    for (local_8 = 0; local_8 < 8; local_8 = local_8 + 1) {
      *(undefined1 *)((int)param_1 + local_8 * 7 + 0x790) = 0;
    }
    if (*(int *)((int)param_1 + 0xc7a) != 0) {
      thunk_FUN_0012b254(*param_1,*(int *)((int)param_1 + 0xc7a),0xffffffff);
    }
    local_10 = (undefined4 *)0x0;
    thunk_FUN_0010544e(0x16,0,0x17,0x27,param_1);
    thunk_FUN_001056aa(0x16,0,param_1);
    local_6 = 0;
    local_8 = 0;
    local_a = 0;
    do {
      if (((local_6 == 0x46) && (0x30 < local_5)) && (local_5 < 0x39)) {
        puVar4 = (undefined4 *)((int)param_1 + local_a * 0x34 + 0x1022);
        if (local_10 != (undefined4 *)0x0) {
          *local_10 = puVar4;
        }
        *puVar4 = 0;
        *(short *)((int)param_1 + local_a * 0x34 + 0x1026) =
             (*(short *)((int)param_1 + 6) + -1) * 8 + 4;
        *(short *)(param_1 + local_a * 0xd + 0x40a) = *(short *)(param_1 + 1) * 8 + 10;
        *(undefined2 *)((int)param_1 + local_a * 0x34 + 0x102a) = 0x10;
        *(undefined2 *)(param_1 + local_a * 0xd + 0x40b) = 8;
        *(undefined2 *)((int)param_1 + local_a * 0x34 + 0x102e) = 3;
        *(undefined2 *)(param_1 + local_a * 0xd + 0x40c) = 0x102;
        *(undefined2 *)((int)param_1 + local_a * 0x34 + 0x1032) = 1;
        param_1[local_a * 0xd + 0x40d] = 0;
        param_1[local_a * 0xd + 0x40e] = 0;
        param_1[local_a * 0xd + 0x40f] = 0;
        param_1[local_a * 0xd + 0x410] = 0;
        param_1[local_a * 0xd + 0x411] = 0;
        *(ushort *)(param_1 + local_a * 0xd + 0x412) = local_5 - 0x31;
        *(undefined4 *)((int)param_1 + local_a * 0x34 + 0x104a) = 0;
        *(undefined1 **)((int)param_1 + local_a * 0x34 + 0x104e) = &LAB_001098e8;
        *(undefined4 **)((int)param_1 + local_a * 0x34 + 0x1052) = param_1;
        local_a = local_a + 1;
        local_10 = puVar4;
      }
      thunk_FUN_001054f8(local_5,param_1);
      if (local_5 == 0xd) {
        local_8 = local_8 + 1;
      }
      local_6 = local_5;
      if (1 < local_8) break;
      local_5 = thunk_FUN_00108086();
    } while (local_5 != 0);
    if (local_a != 0) {
      thunk_FUN_0012b234(*param_1,(int)param_1 + 0x1022,0xffffffff,0xffffffff,0);
    }
LAB_00109cda:
    if (local_5 != 0) {
      local_5 = thunk_FUN_00108086();
      if (local_5 == 0) goto LAB_00109d92;
      sVar3 = local_5 - 0x31;
      if ((-1 < sVar3) && (sVar3 < 8)) {
        local_5 = thunk_FUN_00108086();
        if (local_5 == 0x3d) {
          local_a = 0;
          while( true ) {
            local_5 = thunk_FUN_00108086();
            if ((local_5 == 0) || (local_5 == 0xd)) break;
            if (local_a < 6) {
              *(byte *)((int)param_1 + (int)local_a + sVar3 * 7 + 0x790) = local_5;
              local_a = local_a + 1;
            }
          }
          *(undefined1 *)((int)param_1 + (int)local_a + sVar3 * 7 + 0x790) = 0;
          goto LAB_00109cda;
        }
      }
      while ((local_5 != 0 && (local_5 != 0xd))) {
        local_5 = thunk_FUN_00108086();
      }
      goto LAB_00109cda;
    }
  }
LAB_00109d92:
  local_5 = thunk_FUN_00108086();
  if (local_5 != '\0') {
    thunk_FUN_0010544e(7,1,8,0x1d,param_1);
    thunk_FUN_001056aa(7,1,param_1);
    thunk_FUN_0010506a(param_1);
    do {
      thunk_FUN_001054f8(local_5,param_1);
      if (local_5 == '\r') {
        thunk_FUN_001051de(param_1);
      }
      local_5 = thunk_FUN_00108086();
    } while (local_5 != '\0');
  }
  local_5 = thunk_FUN_00108086();
  if (local_5 != '\0') {
    local_8 = 0;
    do {
      local_a = 0;
      do {
        if (local_a < 8) {
          *(byte *)((int)param_1 + (int)local_a + local_8 * 9 + 0x7c8) = local_5;
          local_a = local_a + 1;
        }
        local_5 = thunk_FUN_00108086();
      } while (((local_5 != '\0') && (local_5 != '\r')) && (local_5 != ','));
      for (; local_a < 8; local_a = local_a + 1) {
        *(undefined1 *)((int)param_1 + (int)local_a + local_8 * 9 + 0x7c8) = 0x20;
      }
      sVar3 = local_8 + 1;
      *(undefined1 *)((int)param_1 + (int)local_a + local_8 * 9 + 0x7c8) = 0;
      if ((local_5 == '\0') || (local_5 == '\r')) break;
      local_5 = thunk_FUN_00108086();
      local_8 = sVar3;
    } while (local_5 != '\0');
    *(short *)((int)param_1 + 0xc72) = sVar3;
    while (local_5 != '\0') {
      local_5 = thunk_FUN_00108086();
    }
  }
  *(undefined2 *)(param_1 + 0x31d) = 0;
  thunk_FUN_001056aa(7,0x1f,param_1);
  thunk_FUN_0010506a(param_1);
  thunk_FUN_0010565e(param_1 + 0x1f2,param_1);
  local_5 = thunk_FUN_00108086();
  if (local_5 != '\0') {
    thunk_FUN_001056aa(10,1,param_1);
    thunk_FUN_00105022(param_1);
    local_8 = 0;
    do {
      for (local_a = 0; local_a < 6; local_a = local_a + 1) {
        *(byte *)((int)param_1 + (int)local_a + local_8 * 0x66 + 0x810) = local_5;
        local_5 = thunk_FUN_00108086();
      }
      *(undefined1 *)((int)param_1 + (int)local_a + local_8 * 0x66 + 0x810) = 0;
      for (local_a = 0; local_a < 0x10; local_a = local_a + 1) {
        uVar1 = thunk_FUN_00108086();
        *(undefined1 *)((int)param_1 + (int)local_a + local_8 * 0x66 + 0x817) = uVar1;
      }
      *(undefined1 *)((int)param_1 + (int)local_a + local_8 * 0x66 + 0x817) = 0;
      thunk_FUN_00108086();
      local_a = 0;
      while( true ) {
        cVar2 = thunk_FUN_00108086();
        if (cVar2 == ',') break;
        *(char *)((int)param_1 + (int)local_a + local_8 * 0x66 + 0x828) = cVar2;
        local_a = local_a + 1;
      }
      for (; local_a < 5; local_a = local_a + 1) {
        *(undefined1 *)((int)param_1 + (int)local_a + local_8 * 0x66 + 0x828) = 0x20;
      }
      *(undefined1 *)((int)param_1 + (int)local_a + local_8 * 0x66 + 0x828) = 0;
      local_a = 0;
      local_c = 0;
      do {
        cVar2 = thunk_FUN_00108086();
        if ((cVar2 == '\r') || (cVar2 == ',')) {
          for (; local_c < 8; local_c = local_c + 1) {
            *(undefined1 *)((int)param_1 + (int)local_c + local_a * 9 + local_8 * 0x66 + 0x82e) =
                 0x20;
          }
          *(undefined1 *)((int)param_1 + (int)local_c + local_a * 9 + local_8 * 0x66 + 0x82e) = 0;
          local_a = local_a + 1;
          local_c = 0;
        }
        else if (local_c < 8) {
          *(char *)((int)param_1 + (int)local_c + local_a * 9 + local_8 * 0x66 + 0x82e) = cVar2;
          local_c = local_c + 1;
        }
      } while (cVar2 != '\r');
      *(undefined2 *)((int)param_1 + 6) = 1;
      thunk_FUN_0010565e((int)param_1 + local_8 * 0x66 + 0x810,param_1);
      *(short *)((int)param_1 + 6) = *(short *)((int)param_1 + 6) + 1;
      thunk_FUN_0010565e((int)param_1 + local_8 * 0x66 + 0x817,param_1);
      *(short *)((int)param_1 + 6) = *(short *)((int)param_1 + 6) + 1;
      thunk_FUN_0010565e((int)param_1 + local_8 * 0x66 + 0x828,param_1);
      *(undefined2 *)((int)param_1 + 6) = 0x1f;
      thunk_FUN_0010565e((int)param_1 + local_8 * 0x66 + 0x82e,param_1);
      thunk_FUN_00105250(param_1);
      thunk_FUN_0010506a(param_1);
      local_8 = local_8 + 1;
      local_5 = thunk_FUN_00108086();
    } while (local_5 != '\0');
    *(short *)((int)param_1 + 0xc76) = local_8;
  }
  *(undefined2 *)(param_1 + 0x31e) = 0xffff;
  FUN_0010935a((int)param_1 + 0xc7a,0);
  return;
}



/* ===== FUN_0010a1e2 @ 0010a1e2 (size 184) ===== */
/* strings: P%02d */

undefined4 FUN_0010a1e2(void)

{
  undefined4 uVar1;
  char cVar2;
  undefined1 auStack_8 [4];
  
  DAT_0011d070 = 2;
  if (DAT_0011d074 == 0) {
    uVar1 = thunk_FUN_00101688(&DAT_0011e3f8);
    thunk_FUN_0011956a(&DAT_0011e3f4,uVar1,1,0x43);
    cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
    if (cVar2 == '@') {
      FUN_00109a5e(DAT_0011d07c);
      uVar1 = 1;
      DAT_0011d074 = 1;
    }
    else {
      uVar1 = 0;
    }
  }
  else {
    thunk_FUN_0010060e(auStack_8,s_P_02d_0011e3fc,(int)*(short *)(DAT_0011d07c + 0xc78));
    uVar1 = thunk_FUN_00101688(auStack_8);
    thunk_FUN_0011956a(auStack_8,uVar1,1,0x43);
    cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
    if (cVar2 == '@') {
      FUN_00109a5e(DAT_0011d07c);
      uVar1 = 1;
    }
    else {
      uVar1 = 0;
    }
  }
  return uVar1;
}



/* ===== FUN_0010a484 @ 0010a484 (size 70) ===== */

undefined4 FUN_0010a484(int param_1)

{
  undefined4 uVar1;
  undefined4 uVar2;
  
  uVar1 = *(undefined4 *)(param_1 + 0x30);
  FUN_00109520(uVar1,*(undefined2 *)(param_1 + 0x26));
  uVar2 = thunk_FUN_0010e0fc();
  FUN_00109520(uVar1,*(undefined2 *)(param_1 + 0x26));
  return uVar2;
}



/* ===== thunk_FUN_0012b214 @ 0010a510 (size 6) ===== */

void thunk_FUN_0012b214(void)

{
  (**(code **)(IntuitionBase + -0x1b0))();    /* = IntuitionBase.RefreshGList() */
  return;
}



/* ===== thunk_FUN_0010565e @ 0010a516 (size 6) ===== */

void thunk_FUN_0010565e(char *param_1,undefined4 param_2)

{
  char cVar1;
  
  while( true ) {
    cVar1 = *param_1;
    param_1 = param_1 + 1;
    if (cVar1 == '\0') break;
    FUN_001054f8(cVar1,param_2);
  }
  return;
}



/* ===== thunk_FUN_0011979e @ 0010a51c (size 6) ===== */

undefined4 thunk_FUN_0011979e(undefined4 param_1)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b8 + 0x28) = param_1;
  *(undefined2 *)(DAT_001230b8 + 0x1c) = 0xb;
  thunk_FUN_001291a4(DAT_001230b8);
  uVar2 = DAT_00120104 | DAT_001230c6 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c6 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230ac), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b8 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011fef2);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 0x40;
    }
    if (cVar1 == '\0') {
      cVar1 = *(char *)(DAT_001230b8 + 0x2c);
      if (cVar1 == 'B') {
        thunk_FUN_00115000(0x42,param_1);
        thunk_FUN_00101638(&DAT_00120170,0x42);
        return 0x40;
      }
      if (cVar1 != 'A') {
        if (cVar1 != '@') {
          return 0x40;
        }
        return 0x40;
      }
      thunk_FUN_00115000(0x41,param_1);
      return 0x41;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011ff00);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 0x40;
}



/* ===== thunk_FUN_00105250 @ 0010a522 (size 6) ===== */

void thunk_FUN_00105250(int param_1)

{
  if ((*(short *)(param_1 + 10) == 0) && (*(short *)(param_1 + 4) < 0x17)) {
    *(short *)(param_1 + 4) = *(short *)(param_1 + 4) + 1;
  }
  *(undefined2 *)(param_1 + 6) = 0;
  *(undefined2 *)(param_1 + 10) = 0;
  *(undefined1 *)(param_1 + 9) = 0;
  return;
}



/* ===== thunk_FUN_0012b234 @ 0010a528 (size 6) ===== */

void thunk_FUN_0012b234(void)

{
  (**(code **)(IntuitionBase + -0x1b6))();    /* = IntuitionBase.AddGList() */
  return;
}



/* ===== thunk_FUN_00101688 @ 0010a52e (size 6) ===== */

int thunk_FUN_00101688(char *param_1)

{
  char *pcVar1;
  char *pcVar2;
  
  pcVar1 = param_1;
  do {
    pcVar2 = pcVar1;
    pcVar1 = pcVar2 + 1;
  } while (*pcVar2 != '\0');
  return (int)pcVar2 - (int)param_1;
}



/* ===== thunk_FUN_001051de @ 0010a53a (size 6) ===== */

void thunk_FUN_001051de(int param_1)

{
  *(short *)(param_1 + 6) = *(short *)(param_1 + 6) + 1;
  if (*(short *)(param_1 + 6) == 0x28) {
    *(undefined2 *)(param_1 + 6) = 0;
    if (*(short *)(param_1 + 4) < 0x17) {
      *(short *)(param_1 + 4) = *(short *)(param_1 + 4) + 1;
    }
  }
  *(undefined2 *)(param_1 + 10) = 0;
  return;
}



/* ===== thunk_FUN_0010b730 @ 0010a546 (size 6) ===== */

undefined4 thunk_FUN_0010b730(void)

{
  char cVar1;
  undefined4 uVar2;
  short sVar3;
  
  DAT_0011d070 = 2;
  DAT_001215c4 = *(short *)(DAT_0011d07c + 0xc78);
  cVar1 = *(char *)(DAT_001215c4 * 0x66 + DAT_0011d07c + 0x828);
  thunk_FUN_0010060e(&DAT_00121588,s_D_02d_0011e5dc,(int)DAT_001215c4);
  sVar3 = 0x24;
  do {
    sVar3 = sVar3 + -6;
    if (sVar3 < 0) {
      thunk_FUN_00115000(1,s_Can_t_download_this_0011e5e2);
      return 0;
    }
  } while ((short)cVar1 != *(short *)(sVar3 + 0x10b780));
                    /* WARNING: Could not recover jumptable at 0x0010b77c. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  uVar2 = (*(code *)(sVar3 + 0x10b782))();
  return uVar2;
}



/* ===== thunk_FUN_0010e0fc @ 0010a54c (size 6) ===== */

undefined4 thunk_FUN_0010e0fc(void)

{
  undefined4 uVar1;
  char cVar2;
  
  DAT_0011d070 = 5;
  thunk_FUN_0010060e(&DAT_00121588,s_D_02d_0011ea6a,(int)*(short *)(DAT_0011d07c + 0xc78));
  do {
    uVar1 = thunk_FUN_00101688(&DAT_00121588);
    thunk_FUN_0011956a(&DAT_00121588,uVar1,1,0x43);
    cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
    if (cVar2 != '@') {
      return 0;
    }
    DAT_0012309c = thunk_FUN_0010818a(DAT_0011d078,&DAT_001220fc);
    thunk_FUN_0011754e(&DAT_001220fc,DAT_0012309c);
    thunk_FUN_00101674(&DAT_00121588,&DAT_0011ea70);
  } while (DAT_001203b2 != 0);
  return 1;
}



/* ===== thunk_FUN_0010506a @ 0010a564 (size 6) ===== */

void thunk_FUN_0010506a(int param_1)

{
  *(undefined1 *)(param_1 + 8) = 6;
  return;
}



/* ===== thunk_FUN_00108086 @ 0010a56a (size 6) ===== */

char thunk_FUN_00108086(void)

{
  if (DAT_001203bb == '\0') {
    DAT_001203ba = (*DAT_001203b6)();
    if (DAT_001203ba == '\x06') {
      DAT_001203ba = ' ';
      DAT_001203bb = (*DAT_001203b6)();
    }
    else if (DAT_001203ba == '\a') {
      DAT_001203ba = (*DAT_001203b6)();
      DAT_001203bb = (*DAT_001203b6)();
    }
  }
  else {
    DAT_001203bb = DAT_001203bb + -1;
  }
  return DAT_001203ba;
}



/* ===== thunk_FUN_00105180 @ 0010a570 (size 6) ===== */

void thunk_FUN_00105180(int param_1)

{
  *(undefined2 *)(param_1 + 4) = 0;
  *(undefined2 *)(param_1 + 6) = 0;
  *(undefined2 *)(param_1 + 10) = 0;
  return;
}



/* ===== thunk_FUN_001056aa @ 0010a57c (size 6) ===== */

void thunk_FUN_001056aa(undefined2 param_1,undefined2 param_2,int param_3)

{
  *(undefined2 *)(param_3 + 4) = param_1;
  *(undefined2 *)(param_3 + 6) = param_2;
  *(undefined2 *)(param_3 + 10) = 0;
  return;
}



/* ===== thunk_FUN_0012a068 @ 0010a594 (size 6) ===== */

void thunk_FUN_0012a068(void)

{
  (**(code **)(GfxBase + -0x132))();    /* = GfxBase.RectFill() */
  return;
}



/* ===== thunk_FUN_0010060e @ 0010a5a6 (size 6) ===== */

undefined4 thunk_FUN_0010060e(undefined1 *param_1,undefined4 param_2)

{
  DAT_001231a0 = 0;
  DAT_0012319c = param_1;
  FUN_00100f46(&LAB_001005f4,param_2,&stack0x0000000c);
  *DAT_0012319c = 0;
  return DAT_001231a0;
}



/* ===== thunk_FUN_00105022 @ 0010a5b2 (size 6) ===== */

void thunk_FUN_00105022(int param_1)

{
  *(undefined1 *)(param_1 + 8) = 2;
  return;
}



/* ===== thunk_FUN_0012a0b8 @ 0010a5b8 (size 6) ===== */

void thunk_FUN_0012a0b8(void)

{
  (**(code **)(GfxBase + -0x162))();    /* = GfxBase.SetDrMd() */
  return;
}



/* ===== thunk_FUN_0012b254 @ 0010a5be (size 6) ===== */

void thunk_FUN_0012b254(void)

{
  (**(code **)(IntuitionBase + -0x1bc))();    /* = IntuitionBase.RemoveGList() */
  return;
}



/* ===== thunk_FUN_0011956a @ 0010a5ca (size 6) ===== */

undefined4
thunk_FUN_0011956a(undefined4 param_1,undefined4 param_2,undefined1 param_3,undefined1 param_4)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b4 + 0x28) = param_1;
  *(undefined4 *)(DAT_001230b4 + 0x24) = param_2;
  *(undefined1 *)(DAT_001230b4 + 0x2c) = param_4;
  *(undefined1 *)(DAT_001230b4 + 0x2d) = param_3;
  *(undefined2 *)(DAT_001230b4 + 0x1c) = 3;
  thunk_FUN_001291a4(DAT_001230b4);
  uVar2 = DAT_00120104 | DAT_001230c2 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c2 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230b0), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b4 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011feba);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 1;
    }
    if (cVar1 == '\0') {
      return 1;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011fec8);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 1;
}



/* ===== thunk_FUN_0010544e @ 0010a5d6 (size 6) ===== */

void thunk_FUN_0010544e(int param_1,int param_2,int param_3,int param_4,int param_5)

{
  int iVar1;
  undefined4 uStack_c;
  undefined4 uStack_8;
  
  for (uStack_8 = param_1; uStack_8 <= param_3; uStack_8 = uStack_8 + 1) {
    for (uStack_c = param_2; uStack_c <= param_4; uStack_c = uStack_c + 1) {
      iVar1 = thunk_FUN_00101604();
      *(undefined1 *)(uStack_c * 2 + iVar1 + param_5 + 0x10) = 0x20;
    }
  }
  thunk_FUN_001061e8(param_1,param_2,param_3,param_4,param_5);
  return;
}



/* ===== thunk_FUN_001054f8 @ 0010a5e8 (size 6) ===== */

void thunk_FUN_001054f8(byte param_1,int param_2)

{
  short sVar1;
  short sVar2;
  char cVar3;
  byte bVar4;
  int iVar5;
  int iVar6;
  byte unaff_D7b;
  
  switch(param_1 >> 5) {
  case 0:
    (*(code *)(&PTR_LAB_0011d8a8)[(short)(ushort)param_1])(param_2);
    return;
  case 1:
    unaff_D7b = param_1;
    break;
  case 2:
    unaff_D7b = param_1 & 0x1f;
    break;
  case 3:
    unaff_D7b = param_1 & 0x1f | 0x40;
    break;
  case 4:
    (*(code *)(&PTR_LAB_0011d928)[param_1 & 0x7f])(param_2);
    return;
  case 5:
    unaff_D7b = param_1 & 0x1f | 0x60;
    break;
  case 6:
    unaff_D7b = param_1 & 0x7f;
    break;
  case 7:
    if (param_1 == 0xff) {
      unaff_D7b = 0x5e;
    }
    else {
      unaff_D7b = param_1 & 0x7f;
    }
  }
  bVar4 = *(byte *)(param_2 + 9) | unaff_D7b;
  sVar1 = *(short *)(param_2 + 4);
  sVar2 = *(short *)(param_2 + 6);
  iVar6 = sVar1 * 0x50;
  iVar5 = sVar2 * 2;
  cVar3 = *(char *)(iVar5 + iVar6 + param_2 + 0x10);
  *(byte *)(iVar5 + iVar6 + param_2 + 0x10) = bVar4;
  *(undefined1 *)(iVar5 + iVar6 + param_2 + 0x11) = *(undefined1 *)(param_2 + 8);
  if ((bVar4 != 0x20) || (cVar3 != ' ')) {
    thunk_FUN_00107000((int)sVar1,(int)sVar2,param_2);
  }
  FUN_001051de(param_2);
  *(short *)(param_2 + 10) = (short)(*(short *)(param_2 + 6) == 0);
  return;
}



/* ===== FUN_0010b000 @ 0010b000 (size 110) ===== */
/* strings: WARNING - CHARGED ITEM */

bool FUN_0010b000(void)

{
  int iVar1;
  undefined1 auStack_1d [20];
  char local_9;
  char *local_8;
  
  local_8 = (char *)(DAT_001215c4 * 0x66 + DAT_0011d07c + 0x82e);
  while( true ) {
    local_9 = *local_8;
    if (local_9 == '\0') {
      return true;
    }
    if (local_9 != ' ') break;
    local_8 = local_8 + 1;
  }
  thunk_FUN_0010060e(auStack_1d,&DAT_0011e41c,local_8);
  iVar1 = thunk_FUN_001104a6(s_WARNING___CHARGED_ITEM_0011e42a,auStack_1d,DAT_001200f8);
  return iVar1 == 1;
}



/* ===== FUN_0010b730 @ 0010b730 (size 102) ===== */
/* strings: Can't download this | D%02d */

undefined4 FUN_0010b730(void)

{
  char cVar1;
  undefined4 uVar2;
  short sVar3;
  
  DAT_0011d070 = 2;
  DAT_001215c4 = *(short *)(DAT_0011d07c + 0xc78);
  cVar1 = *(char *)(DAT_001215c4 * 0x66 + DAT_0011d07c + 0x828);
  thunk_FUN_0010060e(&DAT_00121588,s_D_02d_0011e5dc,(int)DAT_001215c4);
  sVar3 = 0x24;
  do {
    sVar3 = sVar3 + -6;
    if (sVar3 < 0) {
      thunk_FUN_00115000(1,s_Can_t_download_this_0011e5e2);
      return 0;
    }
  } while ((short)cVar1 != *(short *)(sVar3 + 0x10b780));
                    /* WARNING: Could not recover jumptable at 0x0010b77c. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  uVar2 = (*(code *)(sVar3 + 0x10b782))();
  return uVar2;
}



/* ===== thunk_FUN_00115000 @ 0010b82c (size 6) ===== */

void thunk_FUN_00115000(char param_1)

{
  short sVar1;
  
  sVar1 = 0x18;
  do {
    sVar1 = sVar1 + -6;
    if (sVar1 < 0) {
      thunk_FUN_00110472();
      return;
    }
  } while ((short)param_1 != *(short *)(sVar1 + 0x11501a));
                    /* WARNING: Could not recover jumptable at 0x00115016. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*(code *)(sVar1 + 0x11501c))();
  return;
}



/* ===== thunk_FUN_001104a6 @ 0010b844 (size 6) ===== */

void thunk_FUN_001104a6(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  DAT_0011f0b7 = 6;
  DAT_0011f0a0 = param_1;
  DAT_0011f08c = param_2;
  DAT_0011f080 = 7;
  DAT_0011f094 = 7;
  FUN_00110042(param_3,&PTR_DAT_0011f054);
  return;
}



/* ===== thunk_FUN_0010060e @ 0010b874 (size 6) ===== */

undefined4 thunk_FUN_0010060e(undefined1 *param_1,undefined4 param_2)

{
  DAT_001231a0 = 0;
  DAT_0012319c = param_1;
  FUN_00100f46(&LAB_001005f4,param_2,&stack0x0000000c);
  *DAT_0012319c = 0;
  return DAT_001231a0;
}



/* ===== FUN_0010c000 @ 0010c000 (size 48) ===== */
/* strings: Upload filename */

bool FUN_0010c000(void)

{
  int iVar1;
  
  thunk_FUN_00101674(&DAT_0012161e,&DAT_001215f4);
  iVar1 = thunk_FUN_00110390(s_Upload_filename_0011e5f8,&DAT_0012161e,DAT_001200f8);
  return iVar1 == 1;
}



/* ===== FUN_0010c270 @ 0010c270 (size 110) ===== */

undefined4 FUN_0010c270(void)

{
  undefined4 uVar1;
  char cVar2;
  
  uVar1 = thunk_FUN_00101688(&DAT_00121588);
  thunk_FUN_0011956a(&DAT_00121588,uVar1,1,0x43);
  cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
  if (cVar2 == '@') {
    thunk_FUN_00108254(DAT_0011d080);
    cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
    if (cVar2 == '@') {
      DAT_00121589 = 0;
      uVar1 = 1;
    }
    else {
      thunk_FUN_0010d0d0();
      DAT_0011d070 = 2;
      uVar1 = 0;
    }
  }
  else {
    thunk_FUN_0010d0d0();
    DAT_0011d070 = 2;
    uVar1 = 0;
  }
  return uVar1;
}



/* ===== FUN_0010c2de @ 0010c2de (size 26) ===== */

undefined4 FUN_0010c2de(void)

{
  thunk_FUN_0010d0d0();
  if (DAT_00121589 == '\0') {
    DAT_0011d070 = 8;
  }
  else {
    DAT_0011d070 = 2;
  }
  return 1;
}



/* ===== thunk_FUN_0011979e @ 0010c666 (size 6) ===== */

undefined4 thunk_FUN_0011979e(undefined4 param_1)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b8 + 0x28) = param_1;
  *(undefined2 *)(DAT_001230b8 + 0x1c) = 0xb;
  thunk_FUN_001291a4(DAT_001230b8);
  uVar2 = DAT_00120104 | DAT_001230c6 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c6 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230ac), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b8 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011fef2);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 0x40;
    }
    if (cVar1 == '\0') {
      cVar1 = *(char *)(DAT_001230b8 + 0x2c);
      if (cVar1 == 'B') {
        thunk_FUN_00115000(0x42,param_1);
        thunk_FUN_00101638(&DAT_00120170,0x42);
        return 0x40;
      }
      if (cVar1 != 'A') {
        if (cVar1 != '@') {
          return 0x40;
        }
        return 0x40;
      }
      thunk_FUN_00115000(0x41,param_1);
      return 0x41;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011ff00);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 0x40;
}



/* ===== thunk_FUN_00108254 @ 0010c678 (size 6) ===== */

void thunk_FUN_00108254(int param_1)

{
  thunk_FUN_0011956a(param_1 + 0x16,*(undefined4 *)(param_1 + 0x12),1,0x22);
  return;
}



/* ===== thunk_FUN_0010d0d0 @ 0010c67e (size 6) ===== */

void thunk_FUN_0010d0d0(void)

{
  if (DAT_00121650 != 0) {
    thunk_FUN_0011a568(DAT_00121650);
    DAT_00121650 = 0;
  }
  return;
}



/* ===== thunk_FUN_00101688 @ 0010c690 (size 6) ===== */

int thunk_FUN_00101688(char *param_1)

{
  char *pcVar1;
  char *pcVar2;
  
  pcVar1 = param_1;
  do {
    pcVar2 = pcVar1;
    pcVar1 = pcVar2 + 1;
  } while (*pcVar2 != '\0');
  return (int)pcVar2 - (int)param_1;
}



/* ===== thunk_FUN_0011956a @ 0010c6de (size 6) ===== */

undefined4
thunk_FUN_0011956a(undefined4 param_1,undefined4 param_2,undefined1 param_3,undefined1 param_4)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b4 + 0x28) = param_1;
  *(undefined4 *)(DAT_001230b4 + 0x24) = param_2;
  *(undefined1 *)(DAT_001230b4 + 0x2c) = param_4;
  *(undefined1 *)(DAT_001230b4 + 0x2d) = param_3;
  *(undefined2 *)(DAT_001230b4 + 0x1c) = 3;
  thunk_FUN_001291a4(DAT_001230b4);
  uVar2 = DAT_00120104 | DAT_001230c2 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c2 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230b0), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b4 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011feba);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 1;
    }
    if (cVar1 == '\0') {
      return 1;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011fec8);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 1;
}



/* ===== thunk_FUN_00110390 @ 0010c6f0 (size 6) ===== */

void thunk_FUN_00110390(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  FUN_00110306(param_1,param_2,0x20,param_3);
  return;
}



/* ===== thunk_FUN_00101674 @ 0010c6f6 (size 6) ===== */

char * thunk_FUN_00101674(char *param_1,char *param_2)

{
  char cVar1;
  char *pcVar2;
  
  pcVar2 = param_1;
  do {
    cVar1 = *param_2;
    *pcVar2 = cVar1;
    param_2 = param_2 + 1;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  return param_1;
}



/* ===== FUN_0010d000 @ 0010d000 (size 208) ===== */

bool FUN_0010d000(void)

{
  bool bVar1;
  
  DAT_0011e726 = DAT_001200f8;
  DAT_0011e708 = *(short *)(*DAT_0011d07c + 4) + 0x3d;
  DAT_0011e70a = *(short *)(*DAT_0011d07c + 6) + 100;
  DAT_00121650 = thunk_FUN_0011a534(&DAT_0011e708);
  bVar1 = DAT_00121650 != 0;
  if (bVar1) {
    DAT_001215f4 = 0;
    DAT_00121605 = 0;
    DAT_00121607 = 0;
    DAT_0012160e = 0;
    thunk_FUN_0012b088(*(undefined4 *)(DAT_00121650 + 0x32),&DAT_0011e960,0,0);
    thunk_FUN_0012b168(*(undefined4 *)(DAT_00121650 + 0x32),&DAT_0011ea1c,0,0);
    thunk_FUN_0012b06c(*(undefined4 *)(DAT_00121650 + 0x32),&DAT_0011e9b8,0,0);
    thunk_FUN_0012b234(DAT_00121650,&PTR_PTR_0011e934,0xffffffff,0xffffffff,0);
    thunk_FUN_0012b214(&PTR_PTR_0011e934,DAT_00121650,0,0xffffffff);
  }
  return bVar1;
}



/* ===== FUN_0010d0d0 @ 0010d0d0 (size 22) ===== */

void FUN_0010d0d0(void)

{
  if (DAT_00121650 != 0) {
    thunk_FUN_0011a568(DAT_00121650);
    DAT_00121650 = 0;
  }
  return;
}



/* ===== thunk_FUN_0012b214 @ 0010d21a (size 6) ===== */

void thunk_FUN_0012b214(void)

{
  (**(code **)(IntuitionBase + -0x1b0))();    /* = IntuitionBase.RefreshGList() */
  return;
}



/* ===== thunk_FUN_0012b234 @ 0010d220 (size 6) ===== */

void thunk_FUN_0012b234(void)

{
  (**(code **)(IntuitionBase + -0x1b6))();    /* = IntuitionBase.AddGList() */
  return;
}



/* ===== thunk_FUN_0012b06c @ 0010d226 (size 6) ===== */

void thunk_FUN_0012b06c(void)

{
  (**(code **)(IntuitionBase + -0x6c))();    /* = IntuitionBase.DrawBorder() */
  return;
}



/* ===== thunk_FUN_0012b088 @ 0010d238 (size 6) ===== */

void thunk_FUN_0012b088(void)

{
  (**(code **)(IntuitionBase + -0x72))();    /* = IntuitionBase.DrawImage() */
  return;
}



/* ===== thunk_FUN_0011a534 @ 0010d23e (size 6) ===== */

int thunk_FUN_0011a534(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b154(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012b03c,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_0012b168 @ 0010d244 (size 6) ===== */

void thunk_FUN_0012b168(void)

{
  (**(code **)(IntuitionBase + -0xd8))();    /* = IntuitionBase.PrintIText() */
  return;
}



/* ===== thunk_FUN_0011a568 @ 0010d256 (size 6) ===== */

void thunk_FUN_0011a568(undefined4 param_1)

{
  thunk_FUN_0012b03c(param_1);
  FUN_0011a19c(thunk_FUN_0012b03c,param_1);
  return;
}



/* ===== FUN_0010e000 @ 0010e000 (size 88) ===== */

bool FUN_0010e000(void)

{
  undefined4 uVar1;
  char cVar2;
  
  DAT_0011d070 = 2;
  uVar1 = thunk_FUN_00101688(&DAT_0011ea60);
  thunk_FUN_0011956a(&DAT_0011ea5e,uVar1,1,0x43);
  cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
  if (cVar2 == '@') {
    thunk_FUN_00109a5e(DAT_0011d07c);
    thunk_FUN_001091f2(DAT_0011d07c);
    DAT_0011d070 = 5;
  }
  return cVar2 == '@';
}



/* ===== FUN_0010e0fc @ 0010e0fc (size 140) ===== */
/* strings: D%02d */

undefined4 FUN_0010e0fc(void)

{
  undefined4 uVar1;
  char cVar2;
  
  DAT_0011d070 = 5;
  thunk_FUN_0010060e(&DAT_00121588,s_D_02d_0011ea6a,(int)*(short *)(DAT_0011d07c + 0xc78));
  do {
    uVar1 = thunk_FUN_00101688(&DAT_00121588);
    thunk_FUN_0011956a(&DAT_00121588,uVar1,1,0x43);
    cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
    if (cVar2 != '@') {
      return 0;
    }
    DAT_0012309c = thunk_FUN_0010818a(DAT_0011d078,&DAT_001220fc);
    thunk_FUN_0011754e(&DAT_001220fc,DAT_0012309c);
    thunk_FUN_00101674(&DAT_00121588,&DAT_0011ea70);
  } while (DAT_001203b2 != 0);
  return 1;
}



/* ===== FUN_0010e398 @ 0010e398 (size 106) ===== */

undefined4 FUN_0010e398(void)

{
  undefined4 uVar1;
  char cVar2;
  
  uVar1 = thunk_FUN_00101688(&DAT_0011ea92);
  thunk_FUN_0011956a(&DAT_0011ea90,uVar1,1,0x43);
  cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
  if (cVar2 == '@') {
    thunk_FUN_00108254(DAT_0011d080);
    cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
    if (cVar2 == '@') {
      uVar1 = 1;
    }
    else {
      thunk_FUN_0010f18e();
      DAT_0011d070 = 5;
      uVar1 = 0;
    }
  }
  else {
    thunk_FUN_0010f18e();
    DAT_0011d070 = 5;
    uVar1 = 0;
  }
  return uVar1;
}



/* ===== FUN_0010e402 @ 0010e402 (size 46) ===== */

undefined4 FUN_0010e402(void)

{
  undefined4 uVar1;
  
  uVar1 = thunk_FUN_00101688(&DAT_0011ea96);
  thunk_FUN_0011956a(&DAT_0011ea94,uVar1,1,0x43);
  thunk_FUN_0010f18e();
  DAT_0011d070 = 5;
  return 1;
}



/* ===== thunk_FUN_0011979e @ 0010e69e (size 6) ===== */

undefined4 thunk_FUN_0011979e(undefined4 param_1)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b8 + 0x28) = param_1;
  *(undefined2 *)(DAT_001230b8 + 0x1c) = 0xb;
  thunk_FUN_001291a4(DAT_001230b8);
  uVar2 = DAT_00120104 | DAT_001230c6 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c6 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230ac), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b8 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011fef2);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 0x40;
    }
    if (cVar1 == '\0') {
      cVar1 = *(char *)(DAT_001230b8 + 0x2c);
      if (cVar1 == 'B') {
        thunk_FUN_00115000(0x42,param_1);
        thunk_FUN_00101638(&DAT_00120170,0x42);
        return 0x40;
      }
      if (cVar1 != 'A') {
        if (cVar1 != '@') {
          return 0x40;
        }
        return 0x40;
      }
      thunk_FUN_00115000(0x41,param_1);
      return 0x41;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011ff00);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 0x40;
}



/* ===== thunk_FUN_00108254 @ 0010e6b0 (size 6) ===== */

void thunk_FUN_00108254(int param_1)

{
  thunk_FUN_0011956a(param_1 + 0x16,*(undefined4 *)(param_1 + 0x12),1,0x22);
  return;
}



/* ===== thunk_FUN_00109a5e @ 0010e6b6 (size 6) ===== */

void thunk_FUN_00109a5e(undefined4 *param_1)

{
  undefined1 uVar1;
  char cVar2;
  short sVar3;
  undefined4 *puVar4;
  undefined4 *puStack_10;
  short sStack_c;
  short sStack_a;
  short sStack_8;
  byte bStack_6;
  byte bStack_5;
  
  DAT_001203b6 = &LAB_0010a5ac;
  DAT_001203a0 = 0;
  DAT_001203a4 = 0;
  DAT_001203ae = 0;
  DAT_001203ac = 0;
  DAT_001203bb = 0;
  bStack_5 = thunk_FUN_00108086();
  if (bStack_5 != '\0') {
    thunk_FUN_0010544e(0,0,5,0x27,param_1);
    thunk_FUN_00105180(param_1);
    do {
      thunk_FUN_001054f8(bStack_5,param_1);
      bStack_5 = thunk_FUN_00108086();
    } while (bStack_5 != '\0');
  }
  thunk_FUN_0010544e(10,1,0x14,0x1d,param_1);
  thunk_FUN_0010544e(10,0x1f,0x14,0x26,param_1);
  bStack_5 = thunk_FUN_00108086();
  if (bStack_5 != 0) {
    for (sStack_8 = 0; sStack_8 < 8; sStack_8 = sStack_8 + 1) {
      *(undefined1 *)((int)param_1 + sStack_8 * 7 + 0x790) = 0;
    }
    if (*(int *)((int)param_1 + 0xc7a) != 0) {
      thunk_FUN_0012b254(*param_1,*(int *)((int)param_1 + 0xc7a),0xffffffff);
    }
    puStack_10 = (undefined4 *)0x0;
    thunk_FUN_0010544e(0x16,0,0x17,0x27,param_1);
    thunk_FUN_001056aa(0x16,0,param_1);
    bStack_6 = 0;
    sStack_8 = 0;
    sStack_a = 0;
    do {
      if (((bStack_6 == 0x46) && (0x30 < bStack_5)) && (bStack_5 < 0x39)) {
        puVar4 = (undefined4 *)((int)param_1 + sStack_a * 0x34 + 0x1022);
        if (puStack_10 != (undefined4 *)0x0) {
          *puStack_10 = puVar4;
        }
        *puVar4 = 0;
        *(short *)((int)param_1 + sStack_a * 0x34 + 0x1026) =
             (*(short *)((int)param_1 + 6) + -1) * 8 + 4;
        *(short *)(param_1 + sStack_a * 0xd + 0x40a) = *(short *)(param_1 + 1) * 8 + 10;
        *(undefined2 *)((int)param_1 + sStack_a * 0x34 + 0x102a) = 0x10;
        *(undefined2 *)(param_1 + sStack_a * 0xd + 0x40b) = 8;
        *(undefined2 *)((int)param_1 + sStack_a * 0x34 + 0x102e) = 3;
        *(undefined2 *)(param_1 + sStack_a * 0xd + 0x40c) = 0x102;
        *(undefined2 *)((int)param_1 + sStack_a * 0x34 + 0x1032) = 1;
        param_1[sStack_a * 0xd + 0x40d] = 0;
        param_1[sStack_a * 0xd + 0x40e] = 0;
        param_1[sStack_a * 0xd + 0x40f] = 0;
        param_1[sStack_a * 0xd + 0x410] = 0;
        param_1[sStack_a * 0xd + 0x411] = 0;
        *(ushort *)(param_1 + sStack_a * 0xd + 0x412) = bStack_5 - 0x31;
        *(undefined4 *)((int)param_1 + sStack_a * 0x34 + 0x104a) = 0;
        *(undefined1 **)((int)param_1 + sStack_a * 0x34 + 0x104e) = &LAB_001098e8;
        *(undefined4 **)((int)param_1 + sStack_a * 0x34 + 0x1052) = param_1;
        sStack_a = sStack_a + 1;
        puStack_10 = puVar4;
      }
      thunk_FUN_001054f8(bStack_5,param_1);
      if (bStack_5 == 0xd) {
        sStack_8 = sStack_8 + 1;
      }
      bStack_6 = bStack_5;
      if (1 < sStack_8) break;
      bStack_5 = thunk_FUN_00108086();
    } while (bStack_5 != 0);
    if (sStack_a != 0) {
      thunk_FUN_0012b234(*param_1,(int)param_1 + 0x1022,0xffffffff,0xffffffff,0);
    }
LAB_00109cda:
    if (bStack_5 != 0) {
      bStack_5 = thunk_FUN_00108086();
      if (bStack_5 == 0) goto LAB_00109d92;
      sVar3 = bStack_5 - 0x31;
      if ((-1 < sVar3) && (sVar3 < 8)) {
        bStack_5 = thunk_FUN_00108086();
        if (bStack_5 == 0x3d) {
          sStack_a = 0;
          while( true ) {
            bStack_5 = thunk_FUN_00108086();
            if ((bStack_5 == 0) || (bStack_5 == 0xd)) break;
            if (sStack_a < 6) {
              *(byte *)((int)param_1 + (int)sStack_a + sVar3 * 7 + 0x790) = bStack_5;
              sStack_a = sStack_a + 1;
            }
          }
          *(undefined1 *)((int)param_1 + (int)sStack_a + sVar3 * 7 + 0x790) = 0;
          goto LAB_00109cda;
        }
      }
      while ((bStack_5 != 0 && (bStack_5 != 0xd))) {
        bStack_5 = thunk_FUN_00108086();
      }
      goto LAB_00109cda;
    }
  }
LAB_00109d92:
  bStack_5 = thunk_FUN_00108086();
  if (bStack_5 != '\0') {
    thunk_FUN_0010544e(7,1,8,0x1d,param_1);
    thunk_FUN_001056aa(7,1,param_1);
    thunk_FUN_0010506a(param_1);
    do {
      thunk_FUN_001054f8(bStack_5,param_1);
      if (bStack_5 == '\r') {
        thunk_FUN_001051de(param_1);
      }
      bStack_5 = thunk_FUN_00108086();
    } while (bStack_5 != '\0');
  }
  bStack_5 = thunk_FUN_00108086();
  if (bStack_5 != '\0') {
    sStack_8 = 0;
    do {
      sStack_a = 0;
      do {
        if (sStack_a < 8) {
          *(byte *)((int)param_1 + (int)sStack_a + sStack_8 * 9 + 0x7c8) = bStack_5;
          sStack_a = sStack_a + 1;
        }
        bStack_5 = thunk_FUN_00108086();
      } while (((bStack_5 != '\0') && (bStack_5 != '\r')) && (bStack_5 != ','));
      for (; sStack_a < 8; sStack_a = sStack_a + 1) {
        *(undefined1 *)((int)param_1 + (int)sStack_a + sStack_8 * 9 + 0x7c8) = 0x20;
      }
      sVar3 = sStack_8 + 1;
      *(undefined1 *)((int)param_1 + (int)sStack_a + sStack_8 * 9 + 0x7c8) = 0;
      if ((bStack_5 == '\0') || (bStack_5 == '\r')) break;
      bStack_5 = thunk_FUN_00108086();
      sStack_8 = sVar3;
    } while (bStack_5 != '\0');
    *(short *)((int)param_1 + 0xc72) = sVar3;
    while (bStack_5 != '\0') {
      bStack_5 = thunk_FUN_00108086();
    }
  }
  *(undefined2 *)(param_1 + 0x31d) = 0;
  thunk_FUN_001056aa(7,0x1f,param_1);
  thunk_FUN_0010506a(param_1);
  thunk_FUN_0010565e(param_1 + 0x1f2,param_1);
  bStack_5 = thunk_FUN_00108086();
  if (bStack_5 != '\0') {
    thunk_FUN_001056aa(10,1,param_1);
    thunk_FUN_00105022(param_1);
    sStack_8 = 0;
    do {
      for (sStack_a = 0; sStack_a < 6; sStack_a = sStack_a + 1) {
        *(byte *)((int)param_1 + (int)sStack_a + sStack_8 * 0x66 + 0x810) = bStack_5;
        bStack_5 = thunk_FUN_00108086();
      }
      *(undefined1 *)((int)param_1 + (int)sStack_a + sStack_8 * 0x66 + 0x810) = 0;
      for (sStack_a = 0; sStack_a < 0x10; sStack_a = sStack_a + 1) {
        uVar1 = thunk_FUN_00108086();
        *(undefined1 *)((int)param_1 + (int)sStack_a + sStack_8 * 0x66 + 0x817) = uVar1;
      }
      *(undefined1 *)((int)param_1 + (int)sStack_a + sStack_8 * 0x66 + 0x817) = 0;
      thunk_FUN_00108086();
      sStack_a = 0;
      while( true ) {
        cVar2 = thunk_FUN_00108086();
        if (cVar2 == ',') break;
        *(char *)((int)param_1 + (int)sStack_a + sStack_8 * 0x66 + 0x828) = cVar2;
        sStack_a = sStack_a + 1;
      }
      for (; sStack_a < 5; sStack_a = sStack_a + 1) {
        *(undefined1 *)((int)param_1 + (int)sStack_a + sStack_8 * 0x66 + 0x828) = 0x20;
      }
      *(undefined1 *)((int)param_1 + (int)sStack_a + sStack_8 * 0x66 + 0x828) = 0;
      sStack_a = 0;
      sStack_c = 0;
      do {
        cVar2 = thunk_FUN_00108086();
        if ((cVar2 == '\r') || (cVar2 == ',')) {
          for (; sStack_c < 8; sStack_c = sStack_c + 1) {
            *(undefined1 *)((int)param_1 + (int)sStack_c + sStack_a * 9 + sStack_8 * 0x66 + 0x82e) =
                 0x20;
          }
          *(undefined1 *)((int)param_1 + (int)sStack_c + sStack_a * 9 + sStack_8 * 0x66 + 0x82e) = 0
          ;
          sStack_a = sStack_a + 1;
          sStack_c = 0;
        }
        else if (sStack_c < 8) {
          *(char *)((int)param_1 + (int)sStack_c + sStack_a * 9 + sStack_8 * 0x66 + 0x82e) = cVar2;
          sStack_c = sStack_c + 1;
        }
      } while (cVar2 != '\r');
      *(undefined2 *)((int)param_1 + 6) = 1;
      thunk_FUN_0010565e((int)param_1 + sStack_8 * 0x66 + 0x810,param_1);
      *(short *)((int)param_1 + 6) = *(short *)((int)param_1 + 6) + 1;
      thunk_FUN_0010565e((int)param_1 + sStack_8 * 0x66 + 0x817,param_1);
      *(short *)((int)param_1 + 6) = *(short *)((int)param_1 + 6) + 1;
      thunk_FUN_0010565e((int)param_1 + sStack_8 * 0x66 + 0x828,param_1);
      *(undefined2 *)((int)param_1 + 6) = 0x1f;
      thunk_FUN_0010565e((int)param_1 + sStack_8 * 0x66 + 0x82e,param_1);
      thunk_FUN_00105250(param_1);
      thunk_FUN_0010506a(param_1);
      sStack_8 = sStack_8 + 1;
      bStack_5 = thunk_FUN_00108086();
    } while (bStack_5 != '\0');
    *(short *)((int)param_1 + 0xc76) = sStack_8;
  }
  *(undefined2 *)(param_1 + 0x31e) = 0xffff;
  FUN_0010935a((int)param_1 + 0xc7a,0);
  return;
}



/* ===== thunk_FUN_00101688 @ 0010e6bc (size 6) ===== */

int thunk_FUN_00101688(char *param_1)

{
  char *pcVar1;
  char *pcVar2;
  
  pcVar1 = param_1;
  do {
    pcVar2 = pcVar1;
    pcVar1 = pcVar2 + 1;
  } while (*pcVar2 != '\0');
  return (int)pcVar2 - (int)param_1;
}



/* ===== thunk_FUN_0010f18e @ 0010e6c8 (size 6) ===== */

void thunk_FUN_0010f18e(void)

{
  if (DAT_00121698 != 0) {
    thunk_FUN_0011a568(DAT_00121698);
    DAT_00121698 = 0;
  }
  return;
}



/* ===== thunk_FUN_0010060e @ 0010e6d4 (size 6) ===== */

undefined4 thunk_FUN_0010060e(undefined1 *param_1,undefined4 param_2)

{
  DAT_001231a0 = 0;
  DAT_0012319c = param_1;
  FUN_00100f46(&LAB_001005f4,param_2,&stack0x0000000c);
  *DAT_0012319c = 0;
  return DAT_001231a0;
}



/* ===== thunk_FUN_0011754e @ 0010e6da (size 6) ===== */

int thunk_FUN_0011754e(int param_1,undefined4 param_2)

{
  DAT_00120154 = DAT_00120142;
  DAT_0012015a = 4;
  DAT_0012015c = param_1;
  DAT_00120160 = param_2;
  thunk_FUN_001290f4(DAT_0012013e,&DAT_00120146);
  thunk_FUN_00129134(DAT_00120142);
  thunk_FUN_0012910c(DAT_00120142);
  thunk_FUN_001291d0(DAT_00120168 + 0xe);
  if (DAT_0011d080 != 0) {
    *(byte *)(DAT_0011d080 + 0x11) = *(byte *)(DAT_0011d080 + 0x11) & 0xfb;
  }
  DAT_0011d080 = DAT_0012015c;
  *(byte *)(DAT_0012015c + 0x11) = *(byte *)(DAT_0012015c + 0x11) | 4;
  thunk_FUN_001291e4(DAT_00120168 + 0xe);
  return DAT_0011d080;
}



/* ===== thunk_FUN_0010818a @ 0010e6e6 (size 6) ===== */

undefined1 * thunk_FUN_0010818a(int param_1,undefined1 *param_2)

{
  uint uVar1;
  char cVar2;
  
  DAT_001203b6 = FUN_0010800c;
  DAT_001203a0 = 0;
  DAT_001203a4 = 0;
  DAT_001203ac = 0;
  DAT_001203ae = param_2;
  uVar1 = FUN_0010800c();
  DAT_001203b2 = uVar1 & 0x80;
  *param_2 = 0;
  uVar1 = FUN_0010800c();
  *(undefined *)(param_1 + 0xe) = (&DAT_0011e1c0)[uVar1 & 0xf];
  uVar1 = FUN_0010800c();
  *(undefined *)(param_1 + 0xf) = (&DAT_0011e1c0)[uVar1 & 0xf];
  thunk_FUN_0010568c(param_1);
  cVar2 = FUN_0010800c();
  *(ushort *)(param_1 + 0xc) = (ushort)(cVar2 == '\x0e');
  DAT_001203bb = 0;
  while (cVar2 = FUN_00108086(), cVar2 != '\0') {
    thunk_FUN_001054f8(cVar2,param_1);
  }
  return DAT_001203ae;
}



/* ===== thunk_FUN_0011956a @ 0010e6f8 (size 6) ===== */

undefined4
thunk_FUN_0011956a(undefined4 param_1,undefined4 param_2,undefined1 param_3,undefined1 param_4)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b4 + 0x28) = param_1;
  *(undefined4 *)(DAT_001230b4 + 0x24) = param_2;
  *(undefined1 *)(DAT_001230b4 + 0x2c) = param_4;
  *(undefined1 *)(DAT_001230b4 + 0x2d) = param_3;
  *(undefined2 *)(DAT_001230b4 + 0x1c) = 3;
  thunk_FUN_001291a4(DAT_001230b4);
  uVar2 = DAT_00120104 | DAT_001230c2 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c2 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230b0), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b4 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011feba);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 1;
    }
    if (cVar1 == '\0') {
      return 1;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011fec8);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 1;
}



/* ===== thunk_FUN_00101674 @ 0010e710 (size 6) ===== */

char * thunk_FUN_00101674(char *param_1,char *param_2)

{
  char cVar1;
  char *pcVar2;
  
  pcVar2 = param_1;
  do {
    cVar1 = *param_2;
    *pcVar2 = cVar1;
    param_2 = param_2 + 1;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  return param_1;
}



/* ===== thunk_FUN_001091f2 @ 0010e71c (size 6) ===== */

void thunk_FUN_001091f2(undefined4 *param_1)

{
  undefined2 uVar1;
  short sStack_6;
  
  uVar1 = thunk_FUN_0012b254(*param_1,(int)param_1 + 0xf86,5);
  for (sStack_6 = 0; sStack_6 < 5; sStack_6 = sStack_6 + 1) {
    param_1[sStack_6 * 0xd + 0x3b4] = &DAT_0011e376 + sStack_6 * 0x14;
    *(undefined4 *)((int)param_1 + sStack_6 * 0x34 + 0xee2) =
         *(undefined4 *)(&DAT_0011e3da + sStack_6 * 4);
  }
  thunk_FUN_0012b234(*param_1,(int)param_1 + 0xf86,uVar1,5,0);
  thunk_FUN_0012b214((int)param_1 + 0xf86,*param_1,0,5);
  return;
}



/* ===== FUN_0010f000 @ 0010f000 (size 158) ===== */

undefined4 FUN_0010f000(void)

{
  undefined4 uVar1;
  ushort local_6;
  
  DAT_0011eae6 = DAT_001200f8;
  DAT_0011eac8 = *(short *)(*DAT_0011d07c + 4) + 5;
  DAT_0011eaca = *(short *)(*DAT_0011d07c + 6) + 0x4b;
  DAT_00121698 = thunk_FUN_0011a534(&DAT_0011eac8);
  if (DAT_00121698 == 0) {
    uVar1 = 0;
  }
  else {
    DAT_00121658 = 0;
    for (local_6 = 0; local_6 < 5; local_6 = local_6 + 1) {
      (&DAT_00121669)[(short)local_6 * 9] = 0;
    }
    thunk_FUN_0012b088(*(undefined4 *)(DAT_00121698 + 0x32),&DAT_0011ed78,0,0);
    thunk_FUN_0012b06c(*(undefined4 *)(DAT_00121698 + 0x32),&DAT_0011edd0,0,0);
    uVar1 = 1;
  }
  return uVar1;
}



/* ===== FUN_0010f18e @ 0010f18e (size 22) ===== */

void FUN_0010f18e(void)

{
  if (DAT_00121698 != 0) {
    thunk_FUN_0011a568(DAT_00121698);
    DAT_00121698 = 0;
  }
  return;
}



/* ===== thunk_FUN_0012b06c @ 0010f5bc (size 6) ===== */

void thunk_FUN_0012b06c(void)

{
  (**(code **)(IntuitionBase + -0x6c))();    /* = IntuitionBase.DrawBorder() */
  return;
}



/* ===== thunk_FUN_0012b088 @ 0010f5ce (size 6) ===== */

void thunk_FUN_0012b088(void)

{
  (**(code **)(IntuitionBase + -0x72))();    /* = IntuitionBase.DrawImage() */
  return;
}



/* ===== thunk_FUN_0011a534 @ 0010f5d4 (size 6) ===== */

int thunk_FUN_0011a534(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b154(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012b03c,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_0011a568 @ 0010f5e6 (size 6) ===== */

void thunk_FUN_0011a568(undefined4 param_1)

{
  thunk_FUN_0012b03c(param_1);
  FUN_0011a19c(thunk_FUN_0012b03c,param_1);
  return;
}



/* ===== FUN_00110000 @ 00110000 (size 66) ===== */

void FUN_00110000(void)

{
  DAT_0011ef6c = DAT_0011ee84 + -0xb;
  DAT_0011ef68 = DAT_0011ee84 + -0xb;
  DAT_0011ef72 = DAT_0011ee86 + -5;
  DAT_0011ef6e = DAT_0011ee86 + -5;
  DAT_0011ef7e = DAT_0011ee86 + -2;
  DAT_0011ef84 = DAT_0011ee84 + -9;
  DAT_0011ef80 = DAT_0011ee84 + -9;
  DAT_0011ef86 = DAT_0011ee86 + -2;
  return;
}



/* ===== FUN_00110042 @ 00110042 (size 356) ===== */

undefined2 FUN_00110042(int param_1,undefined4 param_2)

{
  int iVar1;
  undefined2 uVar2;
  int in_stack_fffffff0;
  
  if (param_1 == 0) {
    DAT_0011eeae = 1;
  }
  else {
    DAT_0011ee9e = param_1;
    DAT_0011eeae = 0xf;
  }
  iVar1 = thunk_FUN_0012b200(&DAT_0011f080);
  if (0xf0 < iVar1) {
    DAT_0011ee84 = (short)iVar1 + 0x18;
  }
  FUN_001104d8(&DAT_0011f094,DAT_0011ee84 + -8);
  FUN_001104d8(&DAT_0011f080,DAT_0011ee84 + -8);
  DAT_001216a0 = thunk_FUN_0011a534(&DAT_0011ee80);
  if (DAT_001216a0 == 0) {
    uVar2 = 0;
  }
  else {
    DAT_0011f0ac = DAT_0011ee84 + -8;
    thunk_FUN_0012b088(*(undefined4 *)(DAT_001216a0 + 0x32),&DAT_0011f0a8,4,2);
    thunk_FUN_0012b168(*(undefined4 *)(DAT_001216a0 + 0x32),&DAT_0011f094,4,2);
    FUN_00110000();
    thunk_FUN_0012b06c(*(undefined4 *)(DAT_001216a0 + 0x32),&DAT_0011f018,4,2);
    thunk_FUN_0012b234(DAT_001216a0,param_2,0,0xffffffff,0);
    thunk_FUN_0012b214(param_2,DAT_001216a0,0,0xffffffff);
    thunk_FUN_00129134(*(undefined4 *)(DAT_001216a0 + 0x56));
    while( true ) {
      iVar1 = thunk_FUN_0012910c(*(undefined4 *)(DAT_001216a0 + 0x56));
      if (iVar1 == 0) break;
      in_stack_fffffff0 = *(int *)(iVar1 + 0x1c);
      thunk_FUN_00129120(iVar1,iVar1,in_stack_fffffff0,*(undefined4 *)(iVar1 + 0x14));
    }
    thunk_FUN_0011a568(DAT_001216a0,0);
    uVar2 = *(undefined2 *)(in_stack_fffffff0 + 0x26);
  }
  return uVar2;
}



/* ===== FUN_001101a6 @ 001101a6 (size 208) ===== */

bool FUN_001101a6(int param_1)

{
  bool bVar1;
  
  if (param_1 == 0) {
    DAT_0011eeae = 1;
  }
  else {
    DAT_0011ee9e = param_1;
    DAT_0011eeae = 0xf;
  }
  DAT_0011ee84 = 0x108;
  DAT_0011ee86 = 0x32;
  DAT_001216c6 = thunk_FUN_0011a534(&DAT_0011ee80);
  bVar1 = DAT_001216c6 != 0;
  if (bVar1) {
    thunk_FUN_0012b088(*(undefined4 *)(DAT_001216c6 + 0x32),&DAT_0011f10c,4,2);
    thunk_FUN_0012b168(*(undefined4 *)(DAT_001216c6 + 0x32),&DAT_0011eeb0,4,2);
    FUN_00110000();
    thunk_FUN_0012b06c(*(undefined4 *)(DAT_001216c6 + 0x32),&DAT_0011f018,4,2);
    thunk_FUN_0012b234(DAT_001216c6,&PTR_PTR_0011f0e0,0,0xffffffff,0);
    thunk_FUN_0012b214(&PTR_PTR_0011f0e0,DAT_001216c6,0,0xffffffff);
  }
  return bVar1;
}



/* ===== FUN_00110276 @ 00110276 (size 122) ===== */

undefined4 FUN_00110276(void)

{
  short sVar1;
  int iVar2;
  int in_stack_fffffff0;
  
  thunk_FUN_0012b270(&PTR_PTR_0011f0e0,DAT_001216c6,0);
  while( true ) {
    thunk_FUN_00129134(*(undefined4 *)(DAT_001216c6 + 0x56));
    while (iVar2 = thunk_FUN_0012910c(*(undefined4 *)(DAT_001216c6 + 0x56)), iVar2 != 0) {
      in_stack_fffffff0 = *(int *)(iVar2 + 0x1c);
      thunk_FUN_00129120(iVar2,in_stack_fffffff0,*(undefined4 *)(iVar2 + 0x14),iVar2);
    }
    sVar1 = *(short *)(in_stack_fffffff0 + 0x26);
    if ((sVar1 == 1) || (sVar1 == 2)) break;
    if (sVar1 == 0) {
      FUN_001102f0();
      return 0;
    }
  }
  FUN_001102f0();
  return 1;
}



/* ===== FUN_001102f0 @ 001102f0 (size 22) ===== */

void FUN_001102f0(void)

{
  if (DAT_001216c6 != 0) {
    thunk_FUN_0011a568(DAT_001216c6);
    DAT_001216c6 = 0;
  }
  return;
}



/* ===== FUN_00110306 @ 00110306 (size 138) ===== */

void FUN_00110306(undefined4 param_1,undefined4 param_2,ushort param_3,undefined4 param_4)

{
  short sVar1;
  
  DAT_0011eebc = param_1;
  DAT_0011f0bc = param_2;
  DAT_0011f0c6 = param_3 + 1;
  if (param_3 < 0x10) {
    sVar1 = DAT_0011f0c6 * 8;
  }
  else {
    sVar1 = 0x88;
  }
  DAT_0011f0e8 = sVar1;
  DAT_0011f0e4 = thunk_FUN_00101540();
  DAT_0011eefc = sVar1 + 1;
  DAT_0011ef00 = DAT_0011eefc;
  FUN_001104d8(&DAT_0011eeb0,0x100);
  FUN_001101a6(param_4);
  FUN_00110276();
  return;
}



/* ===== FUN_00110390 @ 00110390 (size 32) ===== */

void FUN_00110390(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  FUN_00110306(param_1,param_2,0x20,param_3);
  return;
}



/* ===== FUN_00110472 @ 00110472 (size 52) ===== */

void FUN_00110472(undefined4 param_1,undefined4 param_2,undefined4 param_3,undefined1 param_4,
                 undefined1 param_5)

{
  DAT_0011f0b7 = param_4;
  DAT_0011f0a0 = param_1;
  DAT_0011f08c = param_2;
  DAT_0011f080 = param_5;
  DAT_0011f094 = param_5;
  FUN_00110042(param_3,&DAT_0011f028);
  return;
}



/* ===== FUN_001104a6 @ 001104a6 (size 50) ===== */

void FUN_001104a6(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  DAT_0011f0b7 = 6;
  DAT_0011f0a0 = param_1;
  DAT_0011f08c = param_2;
  DAT_0011f080 = 7;
  DAT_0011f094 = 7;
  FUN_00110042(param_3,&PTR_DAT_0011f054);
  return;
}



/* ===== FUN_001104d8 @ 001104d8 (size 44) ===== */

void FUN_001104d8(int param_1)

{
  undefined4 uVar1;
  undefined2 uVar2;
  
  uVar1 = thunk_FUN_0012b200(param_1);
  uVar2 = thunk_FUN_00101540(uVar1);
  *(undefined2 *)(param_1 + 4) = uVar2;
  return;
}



/* ===== thunk_FUN_00129120 @ 00110504 (size 6) ===== */

void thunk_FUN_00129120(void)

{
  (**(code **)(SysBase + -0x17a))();    /* = SysBase.ReplyMsg() */
  return;
}



/* ===== thunk_FUN_0012b214 @ 0011050a (size 6) ===== */

void thunk_FUN_0012b214(void)

{
  (**(code **)(IntuitionBase + -0x1b0))();    /* = IntuitionBase.RefreshGList() */
  return;
}



/* ===== thunk_FUN_0012b234 @ 00110510 (size 6) ===== */

void thunk_FUN_0012b234(void)

{
  (**(code **)(IntuitionBase + -0x1b6))();    /* = IntuitionBase.AddGList() */
  return;
}



/* ===== thunk_FUN_0012b06c @ 00110516 (size 6) ===== */

void thunk_FUN_0012b06c(void)

{
  (**(code **)(IntuitionBase + -0x6c))();    /* = IntuitionBase.DrawBorder() */
  return;
}



/* ===== thunk_FUN_00129134 @ 0011051c (size 6) ===== */

void thunk_FUN_00129134(void)

{
  (**(code **)(SysBase + -0x180))();    /* = SysBase.WaitPort() */
  return;
}



/* ===== thunk_FUN_0012910c @ 00110522 (size 6) ===== */

void thunk_FUN_0012910c(void)

{
  (**(code **)(SysBase + -0x174))();    /* = SysBase.GetMsg() */
  return;
}



/* ===== thunk_FUN_0012b088 @ 00110528 (size 6) ===== */

void thunk_FUN_0012b088(void)

{
  (**(code **)(IntuitionBase + -0x72))();    /* = IntuitionBase.DrawImage() */
  return;
}



/* ===== thunk_FUN_0011a534 @ 0011052e (size 6) ===== */

int thunk_FUN_0011a534(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b154(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012b03c,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_0012b168 @ 00110534 (size 6) ===== */

void thunk_FUN_0012b168(void)

{
  (**(code **)(IntuitionBase + -0xd8))();    /* = IntuitionBase.PrintIText() */
  return;
}



/* ===== thunk_FUN_0012b200 @ 0011053a (size 6) ===== */

void thunk_FUN_0012b200(void)

{
  (**(code **)(IntuitionBase + -0x14a))();    /* = IntuitionBase.IntuiTextLength() */
  return;
}



/* ===== thunk_FUN_00101540 @ 00110540 (size 6) ===== */

uint thunk_FUN_00101540(void)

{
  ushort uVar3;
  uint uVar1;
  uint uVar2;
  uint in_D0;
  int iVar4;
  uint uVar5;
  uint uVar6;
  uint in_D1;
  uint uVar7;
  bool bVar8;
  
  if ((int)in_D0 < 0) {
    if ((int)in_D1 < 0) {
      iVar4 = FUN_00101572();
      return -iVar4;
    }
    iVar4 = FUN_00101572();
    return -iVar4;
  }
  if ((int)in_D1 < 0) {
    uVar5 = FUN_00101572();
    return uVar5;
  }
  uVar5 = in_D1 << 0x10 | in_D1 >> 0x10;
  uVar3 = (ushort)(in_D1 >> 0x10);
  if (uVar3 == 0) {
    uVar3 = (ushort)(in_D0 >> 0x10);
    uVar5 = (uint)uVar3;
    if (uVar3 != 0) {
      uVar5 = uVar5 % (in_D1 & 0xffff) << 0x10;
    }
    return CONCAT22((short)(uVar5 >> 0x10),(short)in_D0) % (in_D1 & 0xffff);
  }
  uVar7 = 0x10;
  if (uVar3 < 0x80) {
    uVar5 = uVar5 << 8 | (in_D1 & 0xffff) >> 8;
    uVar7 = 8;
  }
  if ((ushort)uVar5 < 0x800) {
    uVar5 = uVar5 << 4 | uVar5 >> 0x1c;
    uVar7 = (uint)(ushort)((short)uVar7 - 4);
  }
  if ((ushort)uVar5 < 0x2000) {
    uVar5 = uVar5 << 2 | uVar5 >> 0x1e;
    uVar7 = (uint)(ushort)((short)uVar7 - 2);
  }
  if (-1 < (short)uVar5) {
    uVar5 = uVar5 << 1 | uVar5 >> 0x1f;
    uVar7 = (uint)(ushort)((short)uVar7 - 1);
  }
  uVar1 = in_D0 >> (uVar7 & 0x3f);
  uVar2 = CONCAT22((short)(uVar1 % (uVar5 & 0xffff)),(short)((in_D0 << 0x10) >> (uVar7 & 0x3f)));
  uVar6 = uVar5 << 0x10 | uVar5 >> 0x10;
  uVar1 = (uVar1 / (uVar5 & 0xffff) & 0xffff) * (uVar5 >> 0x10);
  uVar5 = uVar2 - uVar1;
  if (uVar2 < uVar1) {
    bVar8 = CARRY4(uVar6,uVar5);
    uVar5 = uVar6 + uVar5;
    do {
    } while (!bVar8);
  }
  uVar5 = uVar5 << (uVar7 & 0x3f) | uVar5 >> 0x20 - (uVar7 & 0x3f);
  return uVar5 << 0x10 | uVar5 >> 0x10;
}



/* ===== thunk_FUN_0011a568 @ 00110546 (size 6) ===== */

void thunk_FUN_0011a568(undefined4 param_1)

{
  thunk_FUN_0012b03c(param_1);
  FUN_0011a19c(thunk_FUN_0012b03c,param_1);
  return;
}



/* ===== thunk_FUN_0012b270 @ 0011054c (size 6) ===== */

void thunk_FUN_0012b270(void)

{
  (**(code **)(IntuitionBase + -0x1ce))();    /* = IntuitionBase.ActivateGadget() */
  return;
}



/* ===== FUN_00111000 @ 00111000 (size 36) ===== */

void FUN_00111000(void)

{
  DAT_001216cc = 1;
  DAT_001216d8 = 8;
  DAT_001216d4 = 0;
  DAT_001216d0 = 0;
  DAT_001216dc = &DAT_001216e4;
  DAT_001216e0 = &DAT_001216e4;
  return;
}



/* ===== FUN_00112000 @ 00112000 (size 364) ===== */

undefined4 FUN_00112000(void)

{
  undefined4 uVar1;
  bool bVar2;
  
  DAT_0011f1a6 = DAT_001200f8;
  DAT_00121828 = thunk_FUN_0011a534(&DAT_0011f188);
  if (DAT_00121828 == 0) {
    uVar1 = 0;
  }
  else {
    thunk_FUN_00101674(&DAT_001217ec,&DAT_00120108);
    thunk_FUN_00101674(&DAT_001217fc,&DAT_00120134);
    thunk_FUN_00101674(&DAT_00121805,&DAT_0012011c);
    thunk_FUN_0010060e(&DAT_00121815,&DAT_0011f77a,DAT_0012012c);
    thunk_FUN_0010060e(&DAT_0012181b,&DAT_0011f77e,DAT_0012012e);
    thunk_FUN_0010060e(&DAT_00121821,&DAT_0011f782,DAT_00120132);
    DAT_0011f4aa = (uint)DAT_0012012c;
    DAT_0011f436 = (uint)DAT_0012012e;
    DAT_0011f3c2 = (uint)DAT_00120132;
    bVar2 = (DAT_00120130 & 4) == 0;
    if (bVar2) {
      PTR_DAT_0011f370 = &DAT_0011f342;
      PTR_DAT_0011f310 = &DAT_0011f2b0;
    }
    else {
      PTR_DAT_0011f370 = &DAT_0011f328;
      PTR_DAT_0011f310 = &DAT_0011f2e2;
    }
    DAT_00121826 = (ushort)!bVar2;
    thunk_FUN_0012b088(*(undefined4 *)(DAT_00121828 + 0x32),&DAT_0011f63a,4,2);
    thunk_FUN_0012b168(*(undefined4 *)(DAT_00121828 + 0x32),&DAT_0011f766,4,2);
    thunk_FUN_0012b06c(*(undefined4 *)(DAT_00121828 + 0x32),&DAT_0011f662,4,2);
    thunk_FUN_0012b234(DAT_00121828,&PTR_PTR_0011f60e,0,0xffffffff,0);
    thunk_FUN_0012b214(&PTR_PTR_0011f60e,DAT_00121828,0,0xffffffff);
    uVar1 = 1;
  }
  return uVar1;
}



/* ===== thunk_FUN_0012b214 @ 0011244e (size 6) ===== */

void thunk_FUN_0012b214(void)

{
  (**(code **)(IntuitionBase + -0x1b0))();    /* = IntuitionBase.RefreshGList() */
  return;
}



/* ===== thunk_FUN_0012b234 @ 0011245a (size 6) ===== */

void thunk_FUN_0012b234(void)

{
  (**(code **)(IntuitionBase + -0x1b6))();    /* = IntuitionBase.AddGList() */
  return;
}



/* ===== thunk_FUN_0012b06c @ 00112460 (size 6) ===== */

void thunk_FUN_0012b06c(void)

{
  (**(code **)(IntuitionBase + -0x6c))();    /* = IntuitionBase.DrawBorder() */
  return;
}



/* ===== thunk_FUN_0012b088 @ 0011247e (size 6) ===== */

void thunk_FUN_0012b088(void)

{
  (**(code **)(IntuitionBase + -0x72))();    /* = IntuitionBase.DrawImage() */
  return;
}



/* ===== thunk_FUN_0011a534 @ 00112484 (size 6) ===== */

int thunk_FUN_0011a534(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b154(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012b03c,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_0012b168 @ 0011248a (size 6) ===== */

void thunk_FUN_0012b168(void)

{
  (**(code **)(IntuitionBase + -0xd8))();    /* = IntuitionBase.PrintIText() */
  return;
}



/* ===== thunk_FUN_0010060e @ 001124a2 (size 6) ===== */

undefined4 thunk_FUN_0010060e(undefined1 *param_1,undefined4 param_2)

{
  DAT_001231a0 = 0;
  DAT_0012319c = param_1;
  FUN_00100f46(&LAB_001005f4,param_2,&stack0x0000000c);
  *DAT_0012319c = 0;
  return DAT_001231a0;
}



/* ===== thunk_FUN_00101674 @ 001124ba (size 6) ===== */

char * thunk_FUN_00101674(char *param_1,char *param_2)

{
  char cVar1;
  char *pcVar2;
  
  pcVar2 = param_1;
  do {
    cVar1 = *param_2;
    *pcVar2 = cVar1;
    param_2 = param_2 + 1;
    pcVar2 = pcVar2 + 1;
  } while (cVar1 != '\0');
  return param_1;
}



/* ===== FUN_00113000 @ 00113000 (size 98) ===== */

undefined4 FUN_00113000(void)

{
  undefined4 uVar1;
  char cVar2;
  
  uVar1 = thunk_FUN_00101688(&DAT_00121588);
  thunk_FUN_0011956a(&DAT_00121588,uVar1,1,0x43);
  cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
  if (cVar2 == '@') {
    DAT_0012309c = thunk_FUN_0010818a(DAT_0011d078,&DAT_001220fc);
    thunk_FUN_0011754e(&DAT_001220fc,DAT_0012309c);
    if (DAT_001203b2 != 0) {
      DAT_0011d070 = 3;
    }
    uVar1 = 1;
  }
  else {
    uVar1 = 0;
  }
  return uVar1;
}



/* ===== FUN_00113062 @ 00113062 (size 104) ===== */

undefined4 FUN_00113062(void)

{
  undefined4 uVar1;
  char cVar2;
  
  uVar1 = thunk_FUN_00101688(&DAT_0011f7ce);
  thunk_FUN_0011956a(&DAT_0011f7cc,uVar1,1,0x43);
  cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
  if (cVar2 == '@') {
    DAT_0012309c = thunk_FUN_0010818a(DAT_0011d078,&DAT_001220fc);
    thunk_FUN_0011754e(&DAT_001220fc,DAT_0012309c);
    if (DAT_001203b2 == 0) {
      DAT_0011d070 = 2;
    }
    uVar1 = 1;
  }
  else {
    DAT_0011d070 = 2;
    uVar1 = 0;
  }
  return uVar1;
}



/* ===== FUN_001130ca @ 001130ca (size 30) ===== */

undefined4 FUN_001130ca(void)

{
  undefined4 local_8;
  
  while (DAT_0011d070 == 3) {
    local_8 = FUN_00113062();
  }
  return local_8;
}



/* ===== thunk_FUN_0011979e @ 001130e8 (size 6) ===== */

undefined4 thunk_FUN_0011979e(undefined4 param_1)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b8 + 0x28) = param_1;
  *(undefined2 *)(DAT_001230b8 + 0x1c) = 0xb;
  thunk_FUN_001291a4(DAT_001230b8);
  uVar2 = DAT_00120104 | DAT_001230c6 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c6 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230ac), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b8 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011fef2);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 0x40;
    }
    if (cVar1 == '\0') {
      cVar1 = *(char *)(DAT_001230b8 + 0x2c);
      if (cVar1 == 'B') {
        thunk_FUN_00115000(0x42,param_1);
        thunk_FUN_00101638(&DAT_00120170,0x42);
        return 0x40;
      }
      if (cVar1 != 'A') {
        if (cVar1 != '@') {
          return 0x40;
        }
        return 0x40;
      }
      thunk_FUN_00115000(0x41,param_1);
      return 0x41;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011ff00);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 0x40;
}



/* ===== thunk_FUN_00101688 @ 001130ee (size 6) ===== */

int thunk_FUN_00101688(char *param_1)

{
  char *pcVar1;
  char *pcVar2;
  
  pcVar1 = param_1;
  do {
    pcVar2 = pcVar1;
    pcVar1 = pcVar2 + 1;
  } while (*pcVar2 != '\0');
  return (int)pcVar2 - (int)param_1;
}



/* ===== thunk_FUN_0011754e @ 001130f4 (size 6) ===== */

int thunk_FUN_0011754e(int param_1,undefined4 param_2)

{
  DAT_00120154 = DAT_00120142;
  DAT_0012015a = 4;
  DAT_0012015c = param_1;
  DAT_00120160 = param_2;
  thunk_FUN_001290f4(DAT_0012013e,&DAT_00120146);
  thunk_FUN_00129134(DAT_00120142);
  thunk_FUN_0012910c(DAT_00120142);
  thunk_FUN_001291d0(DAT_00120168 + 0xe);
  if (DAT_0011d080 != 0) {
    *(byte *)(DAT_0011d080 + 0x11) = *(byte *)(DAT_0011d080 + 0x11) & 0xfb;
  }
  DAT_0011d080 = DAT_0012015c;
  *(byte *)(DAT_0012015c + 0x11) = *(byte *)(DAT_0012015c + 0x11) | 4;
  thunk_FUN_001291e4(DAT_00120168 + 0xe);
  return DAT_0011d080;
}



/* ===== thunk_FUN_0010818a @ 001130fa (size 6) ===== */

undefined1 * thunk_FUN_0010818a(int param_1,undefined1 *param_2)

{
  uint uVar1;
  char cVar2;
  
  DAT_001203b6 = FUN_0010800c;
  DAT_001203a0 = 0;
  DAT_001203a4 = 0;
  DAT_001203ac = 0;
  DAT_001203ae = param_2;
  uVar1 = FUN_0010800c();
  DAT_001203b2 = uVar1 & 0x80;
  *param_2 = 0;
  uVar1 = FUN_0010800c();
  *(undefined *)(param_1 + 0xe) = (&DAT_0011e1c0)[uVar1 & 0xf];
  uVar1 = FUN_0010800c();
  *(undefined *)(param_1 + 0xf) = (&DAT_0011e1c0)[uVar1 & 0xf];
  thunk_FUN_0010568c(param_1);
  cVar2 = FUN_0010800c();
  *(ushort *)(param_1 + 0xc) = (ushort)(cVar2 == '\x0e');
  DAT_001203bb = 0;
  while (cVar2 = FUN_00108086(), cVar2 != '\0') {
    thunk_FUN_001054f8(cVar2,param_1);
  }
  return DAT_001203ae;
}



/* ===== thunk_FUN_0011956a @ 00113100 (size 6) ===== */

undefined4
thunk_FUN_0011956a(undefined4 param_1,undefined4 param_2,undefined1 param_3,undefined1 param_4)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b4 + 0x28) = param_1;
  *(undefined4 *)(DAT_001230b4 + 0x24) = param_2;
  *(undefined1 *)(DAT_001230b4 + 0x2c) = param_4;
  *(undefined1 *)(DAT_001230b4 + 0x2d) = param_3;
  *(undefined2 *)(DAT_001230b4 + 0x1c) = 3;
  thunk_FUN_001291a4(DAT_001230b4);
  uVar2 = DAT_00120104 | DAT_001230c2 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c2 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230b0), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b4 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011feba);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 1;
    }
    if (cVar1 == '\0') {
      return 1;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011fec8);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 1;
}



/* ===== FUN_00114000 @ 00114000 (size 80) ===== */

bool FUN_00114000(void)

{
  DAT_00120154 = DAT_00120142;
  DAT_0012015a = 2;
  DAT_0012015c = DAT_0011d080;
  DAT_00120160 = 0;
  DAT_00120164 = 0;
  thunk_FUN_001290f4(DAT_0012013e,&DAT_00120146);
  thunk_FUN_00129134(DAT_00120142);
  thunk_FUN_0012910c(DAT_00120142);
  return DAT_0012015b == '\0';
}



/* ===== FUN_00114050 @ 00114050 (size 86) ===== */

bool FUN_00114050(undefined4 param_1)

{
  DAT_00120154 = DAT_00120142;
  DAT_0012015a = 5;
  DAT_0012015c = param_1;
  DAT_00120160 = 0;
  DAT_00120164 = 0;
  thunk_FUN_001290f4(DAT_0012013e,&DAT_00120146);
  thunk_FUN_00129134(DAT_00120142);
  thunk_FUN_0012910c(DAT_00120142);
  return DAT_0012015b == '\0';
}



/* ===== thunk_FUN_001290f4 @ 001140a8 (size 6) ===== */

void thunk_FUN_001290f4(void)

{
  (**(code **)(SysBase + -0x16e))();    /* = SysBase.PutMsg() */
  return;
}



/* ===== thunk_FUN_00129134 @ 001140ae (size 6) ===== */

void thunk_FUN_00129134(void)

{
  (**(code **)(SysBase + -0x180))();    /* = SysBase.WaitPort() */
  return;
}



/* ===== thunk_FUN_0012910c @ 001140b4 (size 6) ===== */

void thunk_FUN_0012910c(void)

{
  (**(code **)(SysBase + -0x174))();    /* = SysBase.GetMsg() */
  return;
}



/* ===== FUN_00115000 @ 00115000 (size 58) ===== */

void FUN_00115000(char param_1)

{
  short sVar1;
  
  sVar1 = 0x18;
  do {
    sVar1 = sVar1 + -6;
    if (sVar1 < 0) {
      thunk_FUN_00110472();
      return;
    }
  } while ((short)param_1 != *(short *)(sVar1 + 0x11501a));
                    /* WARNING: Could not recover jumptable at 0x00115016. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*(code *)(sVar1 + 0x11501c))();
  return;
}



/* ===== thunk_FUN_00110472 @ 0011525a (size 6) ===== */

void thunk_FUN_00110472(undefined4 param_1,undefined4 param_2,undefined4 param_3,undefined1 param_4,
                       undefined1 param_5)

{
  DAT_0011f0b7 = param_4;
  DAT_0011f0a0 = param_1;
  DAT_0011f08c = param_2;
  DAT_0011f080 = param_5;
  DAT_0011f094 = param_5;
  FUN_00110042(param_3,&DAT_0011f028);
  return;
}



/* ===== FUN_00117000 @ 00117000 (size 190) ===== */

void FUN_00117000(int param_1)

{
  int iVar1;
  int local_e;
  short local_6;
  
  local_e = 0;
  for (local_6 = 0; local_6 < 6; local_6 = local_6 + 1) {
    iVar1 = local_6 * 0x34 + param_1;
    *(int *)(iVar1 + 0x790) = local_e;
    *(short *)(iVar1 + 0x794) = local_6 * 0x36 + 7;
    *(undefined2 *)(iVar1 + 0x796) = 0xcb;
    *(undefined2 *)(iVar1 + 0x798) = 0x32;
    *(undefined2 *)(iVar1 + 0x79a) = 0x10;
    *(undefined2 *)(iVar1 + 0x79c) = 0x107;
    *(undefined2 *)(iVar1 + 0x79e) = 0x102;
    *(undefined2 *)(iVar1 + 0x7a0) = 1;
    *(undefined **)(iVar1 + 0x7a2) = &DAT_0011fa6e;
    *(undefined4 *)(iVar1 + 0x7a6) = 0;
    *(undefined **)(iVar1 + 0x7aa) = &DAT_0011faa4 + local_6 * 0x14;
    *(undefined4 *)(iVar1 + 0x7ae) = 0;
    *(undefined4 *)(iVar1 + 0x7b2) = 0;
    *(short *)(iVar1 + 0x7b6) = local_6;
    *(undefined4 *)(iVar1 + 0x7b8) = 0;
    *(undefined **)(iVar1 + 0x7bc) = (&PTR_LAB_0011fb1c)[local_6];
    *(int *)(iVar1 + 0x7c0) = param_1;
    local_e = iVar1 + 0x790;
  }
  return;
}



/* ===== FUN_001170be @ 001170be (size 76) ===== */

void FUN_001170be(int *param_1,short param_2)

{
  thunk_FUN_0012a0b8(*(undefined4 *)(*param_1 + 0x32),2);
  thunk_FUN_0012a068(*(undefined4 *)(*param_1 + 0x32),param_2 * 0x36 + 7,0xcb,param_2 * 0x36 + 0x38,
                     0xda);
  return;
}



/* ===== FUN_0011710a @ 0011710a (size 242) ===== */

undefined4 FUN_0011710a(void)

{
  short sVar1;
  int *local_8;
  
  if (DAT_0011d080 != (undefined4 *)0x0) {
    thunk_FUN_001291d0(DAT_00120168 + 0xe);
    local_8 = (int *)*DAT_0011d080;
    while (*local_8 != 0) {
      if ((*(byte *)((int)local_8 + 0x11) & 2) == 0) {
        *(byte *)((int)DAT_0011d080 + 0x11) = *(byte *)((int)DAT_0011d080 + 0x11) & 0xfb;
        DAT_0011d080 = local_8;
        *(byte *)((int)local_8 + 0x11) = *(byte *)((int)local_8 + 0x11) | 4;
        thunk_FUN_001291e4(DAT_00120168 + 0xe);
        thunk_FUN_001080da((int)DAT_0011d080 + 0x16,DAT_0011d078);
        return 1;
      }
      thunk_FUN_001291e4(DAT_00120168 + 0xe);
      sVar1 = thunk_FUN_001180bc(&DAT_0011fb34);
      if (sVar1 == 2) {
        return 0;
      }
      if (sVar1 == 1) {
        thunk_FUN_001291d0(DAT_00120168 + 0xe);
        local_8 = (int *)*local_8;
      }
      else if (sVar1 == 0) {
        thunk_FUN_001291d0(DAT_00120168 + 0xe);
      }
    }
    thunk_FUN_001291e4(DAT_00120168 + 0xe);
  }
  return 0;
}



/* ===== FUN_001171fc @ 001171fc (size 248) ===== */

undefined4 FUN_001171fc(void)

{
  short sVar1;
  int local_8;
  
  if (DAT_0011d080 != 0) {
    thunk_FUN_001291d0(DAT_00120168 + 0xe);
    local_8 = *(int *)(DAT_0011d080 + 4);
    while (*(int *)(local_8 + 4) != 0) {
      if ((*(byte *)(local_8 + 0x11) & 2) == 0) {
        *(byte *)(DAT_0011d080 + 0x11) = *(byte *)(DAT_0011d080 + 0x11) & 0xfb;
        DAT_0011d080 = local_8;
        *(byte *)(local_8 + 0x11) = *(byte *)(local_8 + 0x11) | 4;
        thunk_FUN_001291e4(DAT_00120168 + 0xe);
        thunk_FUN_001080da(DAT_0011d080 + 0x16,DAT_0011d078);
        return 1;
      }
      thunk_FUN_001291e4(DAT_00120168 + 0xe);
      sVar1 = thunk_FUN_001180bc(&DAT_0011fb3a);
      if (sVar1 == 2) {
        return 0;
      }
      if (sVar1 == 1) {
        thunk_FUN_001291d0(DAT_00120168 + 0xe);
        local_8 = *(int *)(local_8 + 4);
      }
      else if (sVar1 == 0) {
        thunk_FUN_001291d0(DAT_00120168 + 0xe);
      }
    }
    thunk_FUN_001291e4(DAT_00120168 + 0xe);
  }
  return 0;
}



/* ===== FUN_0011754e @ 0011754e (size 134) ===== */

int FUN_0011754e(int param_1,undefined4 param_2)

{
  DAT_00120154 = DAT_00120142;
  DAT_0012015a = 4;
  DAT_0012015c = param_1;
  DAT_00120160 = param_2;
  thunk_FUN_001290f4(DAT_0012013e,&DAT_00120146);
  thunk_FUN_00129134(DAT_00120142);
  thunk_FUN_0012910c(DAT_00120142);
  thunk_FUN_001291d0(DAT_00120168 + 0xe);
  if (DAT_0011d080 != 0) {
    *(byte *)(DAT_0011d080 + 0x11) = *(byte *)(DAT_0011d080 + 0x11) & 0xfb;
  }
  DAT_0011d080 = DAT_0012015c;
  *(byte *)(DAT_0012015c + 0x11) = *(byte *)(DAT_0012015c + 0x11) | 4;
  thunk_FUN_001291e4(DAT_00120168 + 0xe);
  return DAT_0011d080;
}



/* ===== thunk_FUN_001290f4 @ 001175d4 (size 6) ===== */

void thunk_FUN_001290f4(void)

{
  (**(code **)(SysBase + -0x16e))();    /* = SysBase.PutMsg() */
  return;
}



/* ===== thunk_FUN_00113062 @ 001175da (size 6) ===== */

undefined4 thunk_FUN_00113062(void)

{
  undefined4 uVar1;
  char cVar2;
  
  uVar1 = thunk_FUN_00101688(&DAT_0011f7ce);
  thunk_FUN_0011956a(&DAT_0011f7cc,uVar1,1,0x43);
  cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
  if (cVar2 == '@') {
    DAT_0012309c = thunk_FUN_0010818a(DAT_0011d078,&DAT_001220fc);
    thunk_FUN_0011754e(&DAT_001220fc,DAT_0012309c);
    if (DAT_001203b2 == 0) {
      DAT_0011d070 = 2;
    }
    uVar1 = 1;
  }
  else {
    DAT_0011d070 = 2;
    uVar1 = 0;
  }
  return uVar1;
}



/* ===== thunk_FUN_00129134 @ 001175e6 (size 6) ===== */

void thunk_FUN_00129134(void)

{
  (**(code **)(SysBase + -0x180))();    /* = SysBase.WaitPort() */
  return;
}



/* ===== thunk_FUN_0010e402 @ 001175ec (size 6) ===== */

undefined4 thunk_FUN_0010e402(void)

{
  undefined4 uVar1;
  
  uVar1 = thunk_FUN_00101688(&DAT_0011ea96);
  thunk_FUN_0011956a(&DAT_0011ea94,uVar1,1,0x43);
  thunk_FUN_0010f18e();
  DAT_0011d070 = 5;
  return 1;
}



/* ===== thunk_FUN_0012910c @ 001175f8 (size 6) ===== */

void thunk_FUN_0012910c(void)

{
  (**(code **)(SysBase + -0x174))();    /* = SysBase.GetMsg() */
  return;
}



/* ===== thunk_FUN_001080da @ 00117604 (size 6) ===== */

void thunk_FUN_001080da(undefined4 param_1,int param_2)

{
  uint uVar1;
  char cVar2;
  
  thunk_FUN_001060f6();
  DAT_001203a8 = param_1;
  DAT_001203b6 = FUN_00108000;
  FUN_00108000();
  uVar1 = FUN_00108000();
  *(undefined *)(param_2 + 0xe) = (&DAT_0011e1c0)[uVar1 & 0xf];
  uVar1 = FUN_00108000();
  *(undefined *)(param_2 + 0xf) = (&DAT_0011e1c0)[uVar1 & 0xf];
  thunk_FUN_0010568c(param_2);
  cVar2 = FUN_00108000();
  *(ushort *)(param_2 + 0xc) = (ushort)(cVar2 == '\x0e');
  DAT_001203bb = 0;
  while (cVar2 = FUN_00108086(), cVar2 != '\0') {
    thunk_FUN_001054f8(cVar2,param_2);
  }
  thunk_FUN_0010617c(param_2);
  return;
}



/* ===== thunk_FUN_001180bc @ 0011760a (size 6) ===== */

undefined2 thunk_FUN_001180bc(undefined4 param_1)

{
  int iVar1;
  int in_stack_fffffff0;
  
  DAT_0011fd68 = param_1;
  thunk_FUN_001104d8(&DAT_0011fd5c,0xd0);
  FUN_00118000();
  thunk_FUN_00129134(*(undefined4 *)(DAT_001230a0 + 0x56));
  while( true ) {
    iVar1 = thunk_FUN_0012910c(*(undefined4 *)(DAT_001230a0 + 0x56));
    if (iVar1 == 0) break;
    in_stack_fffffff0 = *(int *)(iVar1 + 0x1c);
    thunk_FUN_00129120(iVar1,in_stack_fffffff0,*(undefined4 *)(iVar1 + 0x14),iVar1);
  }
  FUN_001180a6();
  return *(undefined2 *)(in_stack_fffffff0 + 0x26);
}



/* ===== thunk_FUN_0010e398 @ 00117610 (size 6) ===== */

undefined4 thunk_FUN_0010e398(void)

{
  undefined4 uVar1;
  char cVar2;
  
  uVar1 = thunk_FUN_00101688(&DAT_0011ea92);
  thunk_FUN_0011956a(&DAT_0011ea90,uVar1,1,0x43);
  cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
  if (cVar2 == '@') {
    thunk_FUN_00108254(DAT_0011d080);
    cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
    if (cVar2 == '@') {
      uVar1 = 1;
    }
    else {
      thunk_FUN_0010f18e();
      DAT_0011d070 = 5;
      uVar1 = 0;
    }
  }
  else {
    thunk_FUN_0010f18e();
    DAT_0011d070 = 5;
    uVar1 = 0;
  }
  return uVar1;
}



/* ===== thunk_FUN_0012a068 @ 0011761c (size 6) ===== */

void thunk_FUN_0012a068(void)

{
  (**(code **)(GfxBase + -0x132))();    /* = GfxBase.RectFill() */
  return;
}



/* ===== thunk_FUN_001291d0 @ 00117622 (size 6) ===== */

void thunk_FUN_001291d0(void)

{
  (**(code **)(SysBase + -0x234))();    /* = SysBase.ObtainSemaphore() */
  return;
}



/* ===== thunk_FUN_0010c2de @ 00117628 (size 6) ===== */

undefined4 thunk_FUN_0010c2de(void)

{
  thunk_FUN_0010d0d0();
  if (DAT_00121589 == '\0') {
    DAT_0011d070 = 8;
  }
  else {
    DAT_0011d070 = 2;
  }
  return 1;
}



/* ===== thunk_FUN_0010c270 @ 0011762e (size 6) ===== */

undefined4 thunk_FUN_0010c270(void)

{
  undefined4 uVar1;
  char cVar2;
  
  uVar1 = thunk_FUN_00101688(&DAT_00121588);
  thunk_FUN_0011956a(&DAT_00121588,uVar1,1,0x43);
  cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
  if (cVar2 == '@') {
    thunk_FUN_00108254(DAT_0011d080);
    cVar2 = thunk_FUN_0011979e(&DAT_0012021a);
    if (cVar2 == '@') {
      DAT_00121589 = 0;
      uVar1 = 1;
    }
    else {
      thunk_FUN_0010d0d0();
      DAT_0011d070 = 2;
      uVar1 = 0;
    }
  }
  else {
    thunk_FUN_0010d0d0();
    DAT_0011d070 = 2;
    uVar1 = 0;
  }
  return uVar1;
}



/* ===== thunk_FUN_0012a0b8 @ 00117634 (size 6) ===== */

void thunk_FUN_0012a0b8(void)

{
  (**(code **)(GfxBase + -0x162))();    /* = GfxBase.SetDrMd() */
  return;
}



/* ===== thunk_FUN_001130ca @ 0011763a (size 6) ===== */

undefined4 thunk_FUN_001130ca(void)

{
  undefined4 uStack_8;
  
  while (DAT_0011d070 == 3) {
    uStack_8 = FUN_00113062();
  }
  return uStack_8;
}



/* ===== thunk_FUN_001291e4 @ 00117640 (size 6) ===== */

void thunk_FUN_001291e4(void)

{
  (**(code **)(SysBase + -0x23a))();    /* = SysBase.ReleaseSemaphore() */
  return;
}



/* ===== FUN_00118000 @ 00118000 (size 166) ===== */

bool FUN_00118000(void)

{
  bool bVar1;
  
  DAT_0011fb5e = DAT_001200f8;
  DAT_001230a0 = thunk_FUN_0011a534(&DAT_0011fb40);
  bVar1 = DAT_001230a0 != 0;
  if (bVar1) {
    thunk_FUN_0012b088(*(undefined4 *)(DAT_001230a0 + 0x32),&DAT_0011fcfc,4,2);
    thunk_FUN_0012b168(*(undefined4 *)(DAT_001230a0 + 0x32),&DAT_0011fd5c,4,2);
    thunk_FUN_0012b06c(*(undefined4 *)(DAT_001230a0 + 0x32),&DAT_0011fd24,4,2);
    thunk_FUN_0012b234(DAT_001230a0,&PTR_PTR_0011fcd0,0,0xffffffff,0);
    thunk_FUN_0012b214(&PTR_PTR_0011fcd0,DAT_001230a0,0,0xffffffff);
  }
  return bVar1;
}



/* ===== FUN_001180a6 @ 001180a6 (size 22) ===== */

void FUN_001180a6(void)

{
  if (DAT_001230a0 != 0) {
    thunk_FUN_0011a568(DAT_001230a0);
    DAT_001230a0 = 0;
  }
  return;
}



/* ===== FUN_001180bc @ 001180bc (size 102) ===== */

undefined2 FUN_001180bc(undefined4 param_1)

{
  int iVar1;
  int in_stack_fffffff0;
  
  DAT_0011fd68 = param_1;
  thunk_FUN_001104d8(&DAT_0011fd5c,0xd0);
  FUN_00118000();
  thunk_FUN_00129134(*(undefined4 *)(DAT_001230a0 + 0x56));
  while( true ) {
    iVar1 = thunk_FUN_0012910c(*(undefined4 *)(DAT_001230a0 + 0x56));
    if (iVar1 == 0) break;
    in_stack_fffffff0 = *(int *)(iVar1 + 0x1c);
    thunk_FUN_00129120(iVar1,in_stack_fffffff0,*(undefined4 *)(iVar1 + 0x14),iVar1);
  }
  FUN_001180a6();
  return *(undefined2 *)(in_stack_fffffff0 + 0x26);
}



/* ===== thunk_FUN_00129120 @ 00118124 (size 6) ===== */

void thunk_FUN_00129120(void)

{
  (**(code **)(SysBase + -0x17a))();    /* = SysBase.ReplyMsg() */
  return;
}



/* ===== thunk_FUN_0012b214 @ 0011812a (size 6) ===== */

void thunk_FUN_0012b214(void)

{
  (**(code **)(IntuitionBase + -0x1b0))();    /* = IntuitionBase.RefreshGList() */
  return;
}



/* ===== thunk_FUN_0012b234 @ 00118130 (size 6) ===== */

void thunk_FUN_0012b234(void)

{
  (**(code **)(IntuitionBase + -0x1b6))();    /* = IntuitionBase.AddGList() */
  return;
}



/* ===== thunk_FUN_0012b06c @ 00118136 (size 6) ===== */

void thunk_FUN_0012b06c(void)

{
  (**(code **)(IntuitionBase + -0x6c))();    /* = IntuitionBase.DrawBorder() */
  return;
}



/* ===== thunk_FUN_00129134 @ 0011813c (size 6) ===== */

void thunk_FUN_00129134(void)

{
  (**(code **)(SysBase + -0x180))();    /* = SysBase.WaitPort() */
  return;
}



/* ===== thunk_FUN_0012910c @ 00118142 (size 6) ===== */

void thunk_FUN_0012910c(void)

{
  (**(code **)(SysBase + -0x174))();    /* = SysBase.GetMsg() */
  return;
}



/* ===== thunk_FUN_0012b088 @ 00118148 (size 6) ===== */

void thunk_FUN_0012b088(void)

{
  (**(code **)(IntuitionBase + -0x72))();    /* = IntuitionBase.DrawImage() */
  return;
}



/* ===== thunk_FUN_0011a534 @ 0011814e (size 6) ===== */

int thunk_FUN_0011a534(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b154(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012b03c,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_0012b168 @ 00118154 (size 6) ===== */

void thunk_FUN_0012b168(void)

{
  (**(code **)(IntuitionBase + -0xd8))();    /* = IntuitionBase.PrintIText() */
  return;
}



/* ===== thunk_FUN_001104d8 @ 0011815a (size 6) ===== */

void thunk_FUN_001104d8(int param_1)

{
  undefined4 uVar1;
  undefined2 uVar2;
  
  uVar1 = thunk_FUN_0012b200(param_1);
  uVar2 = thunk_FUN_00101540(uVar1);
  *(undefined2 *)(param_1 + 4) = uVar2;
  return;
}



/* ===== thunk_FUN_0011a568 @ 00118160 (size 6) ===== */

void thunk_FUN_0011a568(undefined4 param_1)

{
  thunk_FUN_0012b03c(param_1);
  FUN_0011a19c(thunk_FUN_0012b03c,param_1);
  return;
}



/* ===== FUN_00119000 @ 00119000 (size 160) ===== */

void FUN_00119000(void)

{
  DAT_0011fda2 = DAT_001200f8;
  DAT_0011fd70 = thunk_FUN_0011a534(&DAT_0011fd84);
  if (DAT_0011fd70 != 0) {
    thunk_FUN_0012b088(*(undefined4 *)(DAT_0011fd70 + 0x32),&DAT_0011fdb4,0,0);
    thunk_FUN_0012b168(*(undefined4 *)(DAT_0011fd70 + 0x32),&DAT_0011fe02,0,0);
    thunk_FUN_0011a636(DAT_0011fd70,DAT_00120100);
    thunk_FUN_0012b0a4(DAT_0011fd70,0x120);
    thunk_FUN_0011a588(DAT_0011fd70,DAT_001201ae);
    thunk_FUN_001020ae();
    *(undefined4 *)(DAT_001230b4 + 0x28) = DAT_001230a8;
    *(undefined2 *)(DAT_001230b4 + 0x1c) = 10;
    thunk_FUN_00129190(DAT_001230b4);
    DAT_0011fd74 = 1;
  }
  return;
}



/* ===== FUN_001190e8 @ 001190e8 (size 260) ===== */
/* strings: %s %02lx */

void FUN_001190e8(int param_1)

{
  short sVar1;
  short local_32;
  undefined1 auStack_2c [40];
  
  if (*(char *)(param_1 + 0x16) == '\x02') {
    sVar1 = 0x1e;
    while (sVar1 = sVar1 + -6, -1 < sVar1) {
      if ((ushort)*(byte *)(param_1 + 0x17) == *(ushort *)(sVar1 + 0x119112)) {
                    /* WARNING: Could not recover jumptable at 0x0011910e. Too many branches */
                    /* WARNING: Treating indirect jump as call */
        (*(code *)(sVar1 + 0x119114))();
        return;
      }
    }
    DAT_0011fe16 = 2;
    thunk_FUN_0012b168(*(undefined4 *)(DAT_0011fd70 + 0x32),&DAT_0011fe16,8,0x26);
  }
  else {
    if (*(char *)(param_1 + 0x16) == '\x01') {
      local_32 = 0x1a;
    }
    else if (*(char *)(param_1 + 0x16) == '\0') {
      local_32 = 0xe;
    }
    sVar1 = 0x36;
    while (sVar1 = sVar1 + -6, -1 < sVar1) {
      if ((ushort)*(byte *)(param_1 + 0x17) == *(ushort *)(sVar1 + 0x1191c8)) {
                    /* WARNING: Could not recover jumptable at 0x001191c4. Too many branches */
                    /* WARNING: Treating indirect jump as call */
        (*(code *)(sVar1 + 0x1191ca))();
        return;
      }
    }
    thunk_FUN_0012b088(*(undefined4 *)(DAT_0011fd70 + 0x32),&DAT_0011fdc8,8,0x26);
    thunk_FUN_0010060e(auStack_2c,s__s__02lx_0011fea4,&DAT_0011fea0,*(undefined4 *)(param_1 + 0x18))
    ;
    DAT_0011fe22 = auStack_2c;
    DAT_0011fe16 = 6;
    thunk_FUN_0012b168(*(undefined4 *)(DAT_0011fd70 + 0x32),&DAT_0011fe16,0x58,(int)local_32);
  }
  return;
}



/* ===== FUN_00119506 @ 00119506 (size 100) ===== */

void FUN_00119506(void)

{
  int iVar1;
  short sVar2;
  ushort uVar3;
  int iVar4;
  
  iVar4 = thunk_FUN_0012910c(DAT_00120100);
  if (iVar4 != 0) {
    iVar1 = *(int *)(iVar4 + 0x14);
    sVar2 = *(short *)(iVar4 + 0x18);
    uVar3 = *(ushort *)(iVar4 + 0x1a);
    thunk_FUN_00129120(iVar4);
    if (((iVar1 == 0x400) && (sVar2 == 0x5f)) && ((uVar3 & 0x40) != 0)) {
      thunk_FUN_00101638(&DAT_00120170,1);
    }
  }
  return;
}



/* ===== FUN_0011956a @ 0011956a (size 274) ===== */
/* strings: Carrier lost | Comms problem */

undefined4 FUN_0011956a(undefined4 param_1,undefined4 param_2,undefined1 param_3,undefined1 param_4)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b4 + 0x28) = param_1;
  *(undefined4 *)(DAT_001230b4 + 0x24) = param_2;
  *(undefined1 *)(DAT_001230b4 + 0x2c) = param_4;
  *(undefined1 *)(DAT_001230b4 + 0x2d) = param_3;
  *(undefined2 *)(DAT_001230b4 + 0x1c) = 3;
  thunk_FUN_001291a4(DAT_001230b4);
  uVar2 = DAT_00120104 | DAT_001230c2 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c2 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230b0), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b4 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011feba);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 1;
    }
    if (cVar1 == '\0') {
      return 1;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011fec8);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 1;
}



/* ===== FUN_0011967c @ 0011967c (size 290) ===== */
/* strings: Carrier lost | Comms problem */

undefined4
FUN_0011967c(undefined4 param_1,undefined4 param_2,undefined1 *param_3,undefined1 *param_4,
            undefined4 *param_5)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b8 + 0x28) = param_1;
  *(undefined4 *)(DAT_001230b8 + 0x24) = param_2;
  *(undefined2 *)(DAT_001230b8 + 0x1c) = 2;
  thunk_FUN_001291a4(DAT_001230b8);
  uVar2 = DAT_00120104 | DAT_001230c6 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c6 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230ac), iVar4 == 0));
  *param_4 = *(undefined1 *)(DAT_001230b8 + 0x2c);
  *param_3 = *(undefined1 *)(DAT_001230b8 + 0x2d);
  *param_5 = *(undefined4 *)(DAT_001230b8 + 0x20);
  cVar1 = *(char *)(DAT_001230b8 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011fed6);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 1;
    }
    if (cVar1 == '\0') {
      return 1;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011fee4);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 1;
}



/* ===== FUN_0011979e @ 0011979e (size 322) ===== */
/* strings: Carrier lost | Comms problem */

undefined4 FUN_0011979e(undefined4 param_1)

{
  char cVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  
  *(undefined4 *)(DAT_001230b8 + 0x28) = param_1;
  *(undefined2 *)(DAT_001230b8 + 0x1c) = 0xb;
  thunk_FUN_001291a4(DAT_001230b8);
  uVar2 = DAT_00120104 | DAT_001230c6 | DAT_001230be;
  do {
    uVar3 = thunk_FUN_00129090(uVar2);
    if ((DAT_001230be & uVar3) != 0) {
      iVar4 = thunk_FUN_0012910c(DAT_001230a8);
      if (DAT_0011fd74 != 0) {
        FUN_001190e8(iVar4);
      }
      *(undefined2 *)(iVar4 + 0x14) = 0;
    }
    if ((DAT_00120104 & uVar3) != 0) {
      FUN_00119506();
    }
  } while (((DAT_001230c6 & uVar3) == 0) || (iVar4 = thunk_FUN_0012910c(DAT_001230ac), iVar4 == 0));
  cVar1 = *(char *)(DAT_001230b8 + 0x1f);
  if (cVar1 != '\a') {
    if (cVar1 == '\t') {
      thunk_FUN_00115000(0x42,s_Carrier_lost_0011fef2);
      thunk_FUN_00101638(&DAT_00120170,9);
      return 0x40;
    }
    if (cVar1 == '\0') {
      cVar1 = *(char *)(DAT_001230b8 + 0x2c);
      if (cVar1 == 'B') {
        thunk_FUN_00115000(0x42,param_1);
        thunk_FUN_00101638(&DAT_00120170,0x42);
        return 0x40;
      }
      if (cVar1 != 'A') {
        if (cVar1 != '@') {
          return 0x40;
        }
        return 0x40;
      }
      thunk_FUN_00115000(0x41,param_1);
      return 0x41;
    }
  }
  thunk_FUN_00115000(0x42,s_Comms_problem_0011ff00);
  thunk_FUN_00101638(&DAT_00120170,7);
  return 0x40;
}



/* ===== thunk_FUN_001020ae @ 00119ac4 (size 6) ===== */

void thunk_FUN_001020ae(void)

{
  thunk_FUN_0012b1b0(DAT_001200fc,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  if (DAT_0011d078 != (undefined4 *)0x0) {
    thunk_FUN_0012b1b0(*DAT_0011d078,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  if (DAT_0011d07c != (undefined4 *)0x0) {
    thunk_FUN_0012b1b0(*DAT_0011d07c,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  if (DAT_00121650 != 0) {
    thunk_FUN_0012b1b0(DAT_00121650,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  if (DAT_00121698 != 0) {
    thunk_FUN_0012b1b0(DAT_00121698,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  if (DAT_0011fd70 != 0) {
    thunk_FUN_0012b1b0(DAT_0011fd70,PTR_DAT_0011d068,0xb,0xb,0xfffffffb,0);
  }
  return;
}



/* ===== thunk_FUN_00129120 @ 00119aca (size 6) ===== */

void thunk_FUN_00129120(void)

{
  (**(code **)(SysBase + -0x17a))();    /* = SysBase.ReplyMsg() */
  return;
}



/* ===== thunk_FUN_00129190 @ 00119ad0 (size 6) ===== */

void thunk_FUN_00129190(void)

{
  (**(code **)(SysBase + -0x1c8))();    /* = SysBase.DoIO() */
  return;
}



/* ===== thunk_FUN_00115000 @ 00119ad6 (size 6) ===== */

void thunk_FUN_00115000(char param_1)

{
  short sVar1;
  
  sVar1 = 0x18;
  do {
    sVar1 = sVar1 + -6;
    if (sVar1 < 0) {
      thunk_FUN_00110472();
      return;
    }
  } while ((short)param_1 != *(short *)(sVar1 + 0x11501a));
                    /* WARNING: Could not recover jumptable at 0x00115016. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*(code *)(sVar1 + 0x11501c))();
  return;
}



/* ===== thunk_FUN_0011a588 @ 00119ae2 (size 6) ===== */

void thunk_FUN_0011a588(undefined4 param_1,undefined4 param_2)

{
  thunk_FUN_0012b198(param_1,param_2);
  FUN_0011a16c(&LAB_0011a8ce,param_1,0);
  return;
}



/* ===== thunk_FUN_0012910c @ 00119ae8 (size 6) ===== */

void thunk_FUN_0012910c(void)

{
  (**(code **)(SysBase + -0x174))();    /* = SysBase.GetMsg() */
  return;
}



/* ===== thunk_FUN_0011a636 @ 00119aee (size 6) ===== */

undefined4 thunk_FUN_0011a636(int param_1,undefined4 param_2)

{
  if (*(int *)(param_1 + 0x56) == 0) {
    *(undefined4 *)(param_1 + 0x56) = param_2;
    FUN_0011a16c(&LAB_0011a5d0,param_1,param_2);
  }
  else {
    param_2 = *(undefined4 *)(param_1 + 0x56);
  }
  return param_2;
}



/* ===== thunk_FUN_0012b088 @ 00119b00 (size 6) ===== */

void thunk_FUN_0012b088(void)

{
  (**(code **)(IntuitionBase + -0x72))();    /* = IntuitionBase.DrawImage() */
  return;
}



/* ===== thunk_FUN_0011a534 @ 00119b06 (size 6) ===== */

int thunk_FUN_0011a534(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b154(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012b03c,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_0012b168 @ 00119b0c (size 6) ===== */

void thunk_FUN_0012b168(void)

{
  (**(code **)(IntuitionBase + -0xd8))();    /* = IntuitionBase.PrintIText() */
  return;
}



/* ===== thunk_FUN_0010060e @ 00119b1e (size 6) ===== */

undefined4 thunk_FUN_0010060e(undefined1 *param_1,undefined4 param_2)

{
  DAT_001231a0 = 0;
  DAT_0012319c = param_1;
  FUN_00100f46(&LAB_001005f4,param_2,&stack0x0000000c);
  *DAT_0012319c = 0;
  return DAT_001231a0;
}



/* ===== thunk_FUN_001291a4 @ 00119b2a (size 6) ===== */

void thunk_FUN_001291a4(void)

{
  (**(code **)(SysBase + -0x1ce))();    /* = SysBase.SendIO() */
  return;
}



/* ===== thunk_FUN_00129090 @ 00119b3c (size 6) ===== */

void thunk_FUN_00129090(void)

{
  (**(code **)(SysBase + -0x13e))();    /* = SysBase.Wait() */
  return;
}



/* ===== thunk_FUN_00101638 @ 00119b4e (size 6) ===== */

undefined8 thunk_FUN_00101638(undefined4 *param_1,int param_2)

{
  undefined4 uVar1;
  
  if (param_2 == 0) {
    param_2 = 1;
  }
  uVar1 = param_1[1];
  *(undefined4 *)param_1[0xe] = *param_1;
  return CONCAT44(param_2,uVar1);
}



/* ===== thunk_FUN_0012b0a4 @ 00119b60 (size 6) ===== */

void thunk_FUN_0012b0a4(void)

{
  (**(code **)(IntuitionBase + -0x96))();    /* = IntuitionBase.ModifyIDCMP() */
  return;
}



/* ===== FUN_0011a000 @ 0011a000 (size 10) ===== */

char FUN_0011a000(void)

{
  DAT_0011ff2a = DAT_0011ff2a + '\x01';
  return DAT_0011ff2a;
}



/* ===== FUN_0011a00a @ 0011a00a (size 74) ===== */

char FUN_0011a00a(void)

{
  undefined4 local_8;
  
  local_8 = (int *)PTR_DAT_0011ff1c;
  while ((DAT_0011ff2a == *(char *)((int)local_8 + 9) && ((int *)*local_8 != (int *)0x0))) {
    *(char *)((int)local_8 + 9) = *(char *)((int)local_8 + 9) + -1;
    local_8 = (int *)*local_8;
  }
  DAT_0011ff2a = DAT_0011ff2a + -1;
  return DAT_0011ff2a;
}



/* ===== FUN_0011a054 @ 0011a054 (size 92) ===== */

void FUN_0011a054(int param_1)

{
  undefined4 uVar1;
  
  if (*(int *)(param_1 + 0xe) == 0) {
    uVar1 = *(undefined4 *)(param_1 + 0x12);
    thunk_FUN_00129068(param_1,uVar1);
    thunk_FUN_00129038(param_1,uVar1);
  }
  else {
    (**(code **)(param_1 + 0xe))(*(undefined4 *)(param_1 + 0x12),*(undefined4 *)(param_1 + 0x16));
    thunk_FUN_00129068(param_1);
    thunk_FUN_00129038(param_1,0x1a);
  }
  return;
}



/* ===== FUN_0011a0b0 @ 0011a0b0 (size 64) ===== */

char FUN_0011a0b0(void)

{
  int *piVar1;
  undefined4 local_8;
  
  local_8 = (int *)PTR_DAT_0011ff1c;
  while ((*(char *)((int)local_8 + 9) == DAT_0011ff2a &&
         (piVar1 = (int *)*local_8, piVar1 != (int *)0x0))) {
    FUN_0011a054(local_8);
    local_8 = piVar1;
  }
  DAT_0011ff2a = DAT_0011ff2a + -1;
  return DAT_0011ff2a;
}



/* ===== FUN_0011a0f0 @ 0011a0f0 (size 46) ===== */

void FUN_0011a0f0(void)

{
  int *piVar1;
  undefined4 local_8;
  
  local_8 = (int *)PTR_DAT_0011ff1c;
  while( true ) {
    piVar1 = (int *)*local_8;
    if (piVar1 == (int *)0x0) break;
    FUN_0011a054(local_8);
    local_8 = piVar1;
  }
  return;
}



/* ===== FUN_0011a11e @ 0011a11e (size 20) ===== */

void FUN_0011a11e(undefined4 param_1)

{
  FUN_0011a0f0();
  thunk_FUN_00100240(param_1);
  return;
}



/* ===== FUN_0011a132 @ 0011a132 (size 58) ===== */

void FUN_0011a132(int param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4)

{
  *(undefined1 *)(param_1 + 9) = DAT_0011ff2a;
  *(undefined1 *)(param_1 + 8) = 0x2a;
  *(undefined4 *)(param_1 + 10) = 0;
  *(undefined4 *)(param_1 + 0xe) = param_2;
  *(undefined4 *)(param_1 + 0x12) = param_3;
  *(undefined4 *)(param_1 + 0x16) = param_4;
  thunk_FUN_00129050(&PTR_DAT_0011ff1c,param_1);
  return;
}



/* ===== FUN_0011a16c @ 0011a16c (size 48) ===== */

void FUN_0011a16c(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00129020(0x1a,0);
  if (iVar1 != 0) {
    FUN_0011a132(iVar1,param_1,param_2,param_3,iVar1);
  }
  return;
}



/* ===== FUN_0011a19c @ 0011a19c (size 82) ===== */

void FUN_0011a19c(int param_1,int param_2)

{
  int *piVar1;
  int *local_8;
  
  local_8 = (int *)PTR_DAT_0011ff1c;
  piVar1 = local_8;
  do {
    local_8 = piVar1;
    piVar1 = (int *)*local_8;
    if (piVar1 == (int *)0x0) {
      return;
    }
  } while ((*(int *)((int)local_8 + 0xe) != param_1) || (*(int *)((int)local_8 + 0x12) != param_2));
  thunk_FUN_00129068(local_8);
  thunk_FUN_00129038(local_8,0x1a);
  return;
}



/* ===== FUN_0011a1ee @ 0011a1ee (size 74) ===== */

int FUN_0011a1ee(int param_1,undefined4 param_2)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00129020(param_1 + 0x20,param_2);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a132(iVar1,0,param_1 + 0x20,0);
    iVar1 = iVar1 + 0x20;
  }
  return iVar1;
}



/* ===== FUN_0011a238 @ 0011a238 (size 52) ===== */

void FUN_0011a238(int param_1)

{
  int iVar1;
  undefined4 uVar2;
  
  iVar1 = param_1 + -0x20;
  uVar2 = *(undefined4 *)(param_1 + -0xe);
  thunk_FUN_00129068(iVar1,uVar2,iVar1);
  thunk_FUN_00129038(iVar1,uVar2);
  return;
}



/* ===== FUN_0011a290 @ 0011a290 (size 56) ===== */

int FUN_0011a290(undefined4 param_1,undefined4 param_2)

{
  int iVar1;
  
  iVar1 = thunk_FUN_001291b8(param_1,param_2);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(&LAB_0011a976,iVar1,0);
  }
  return iVar1;
}



/* ===== FUN_0011a344 @ 0011a344 (size 56) ===== */

int FUN_0011a344(undefined4 param_1,undefined4 param_2)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00128068(param_1,param_2);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_00128084,iVar1,0);
  }
  return iVar1;
}



/* ===== FUN_0011a3a6 @ 0011a3a6 (size 32) ===== */

void FUN_0011a3a6(undefined4 param_1)

{
  thunk_FUN_00128084(param_1);
  FUN_0011a19c(thunk_FUN_00128084,param_1);
  return;
}



/* ===== FUN_0011a3c6 @ 0011a3c6 (size 56) ===== */

int FUN_0011a3c6(undefined4 param_1,undefined4 param_2)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00128000(param_1,param_2);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012801c,iVar1,0);
  }
  return iVar1;
}



/* ===== FUN_0011a3fe @ 0011a3fe (size 32) ===== */

void FUN_0011a3fe(undefined4 param_1)

{
  thunk_FUN_0012801c(param_1);
  FUN_0011a19c(thunk_FUN_0012801c,param_1);
  return;
}



/* ===== FUN_0011a41e @ 0011a41e (size 194) ===== */

int FUN_0011a41e(undefined4 param_1)

{
  int iVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  
  FUN_0011a000();
  iVar1 = FUN_0011a344(param_1,0xfffffffe);
  if (((iVar1 != 0) && (iVar2 = FUN_0011a1ee(0x104,0), iVar2 != 0)) &&
     (iVar3 = thunk_FUN_00128098(iVar1,iVar2), iVar3 != 0)) {
    FUN_0011a3a6(iVar1);
    iVar1 = *(int *)(iVar2 + 0x7c);
    FUN_0011a238(iVar2);
    iVar2 = FUN_0011a1ee(iVar1,0);
    if (((iVar2 != 0) && (iVar3 = FUN_0011a3c6(param_1,0x3ed), iVar3 != 0)) &&
       (iVar4 = thunk_FUN_00128030(iVar3,iVar2,iVar1), iVar4 == iVar1)) {
      FUN_0011a3fe(iVar3);
      FUN_0011a00a();
      return iVar2;
    }
  }
  FUN_0011a0b0();
  return 0;
}



/* ===== FUN_0011a4e0 @ 0011a4e0 (size 52) ===== */

int FUN_0011a4e0(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b140(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(&LAB_0011a970,iVar1,0);
  }
  return iVar1;
}



/* ===== FUN_0011a534 @ 0011a534 (size 52) ===== */

int FUN_0011a534(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_0012b154(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(thunk_FUN_0012b03c,iVar1,0);
  }
  return iVar1;
}



/* ===== FUN_0011a568 @ 0011a568 (size 32) ===== */

void FUN_0011a568(undefined4 param_1)

{
  thunk_FUN_0012b03c(param_1);
  FUN_0011a19c(thunk_FUN_0012b03c,param_1);
  return;
}



/* ===== FUN_0011a588 @ 0011a588 (size 40) ===== */

void FUN_0011a588(undefined4 param_1,undefined4 param_2)

{
  thunk_FUN_0012b198(param_1,param_2);
  FUN_0011a16c(&LAB_0011a8ce,param_1,0);
  return;
}



/* ===== FUN_0011a636 @ 0011a636 (size 52) ===== */

undefined4 FUN_0011a636(int param_1,undefined4 param_2)

{
  if (*(int *)(param_1 + 0x56) == 0) {
    *(undefined4 *)(param_1 + 0x56) = param_2;
    FUN_0011a16c(&LAB_0011a5d0,param_1,param_2);
  }
  else {
    param_2 = *(undefined4 *)(param_1 + 0x56);
  }
  return param_2;
}



/* ===== FUN_0011a75c @ 0011a75c (size 62) ===== */

int FUN_0011a75c(undefined4 param_1,char param_2)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00125000(param_1,(int)(short)param_2);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(&LAB_0011a910,iVar1,0);
  }
  return iVar1;
}



/* ===== FUN_0011a868 @ 0011a868 (size 52) ===== */

int FUN_0011a868(undefined4 param_1)

{
  int iVar1;
  
  iVar1 = thunk_FUN_001280d0(param_1);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a16c(&LAB_0011a928,iVar1,0);
  }
  return iVar1;
}



/* ===== thunk_FUN_00125000 @ 0011a8c2 (size 6) ===== */

int thunk_FUN_00125000(int param_1,undefined1 param_2)

{
  byte bVar3;
  int iVar1;
  undefined4 uVar2;
  
  bVar3 = FUN_001290a4(0xffffffff);
  if (bVar3 == 0xffffffff) {
    iVar1 = 0;
  }
  else {
    iVar1 = FUN_00129020(0x22,0x10001);
    if (iVar1 == 0) {
      FUN_001290b8((uint)bVar3);
      iVar1 = 0;
    }
    else {
      *(int *)(iVar1 + 10) = param_1;
      *(undefined1 *)(iVar1 + 9) = param_2;
      *(undefined1 *)(iVar1 + 8) = 4;
      *(undefined1 *)(iVar1 + 0xe) = 0;
      *(byte *)(iVar1 + 0xf) = bVar3;
      uVar2 = FUN_0012907c(0);
      *(undefined4 *)(iVar1 + 0x10) = uVar2;
      if (param_1 == 0) {
        FUN_00124000(iVar1 + 0x14);
      }
      else {
        FUN_001290cc(iVar1);
      }
    }
  }
  return iVar1;
}



/* ===== thunk_FUN_00129120 @ 0011a8c8 (size 6) ===== */

void thunk_FUN_00129120(void)

{
  (**(code **)(SysBase + -0x17a))();    /* = SysBase.ReplyMsg() */
  return;
}



/* ===== thunk_FUN_00128000 @ 0011a8d4 (size 6) ===== */

void thunk_FUN_00128000(void)

{
  (**(code **)(DOSBase + -0x1e))();    /* = DOSBase.Open() */
  return;
}



/* ===== thunk_FUN_0012b140 @ 0011a8da (size 6) ===== */

void thunk_FUN_0012b140(void)

{
  (**(code **)(IntuitionBase + -0xc6))();    /* = IntuitionBase.OpenScreen() */
  return;
}



/* ===== thunk_FUN_0012b154 @ 0011a8e0 (size 6) ===== */

void thunk_FUN_0012b154(void)

{
  (**(code **)(IntuitionBase + -0xcc))();    /* = IntuitionBase.OpenWindow() */
  return;
}



/* ===== thunk_FUN_00129038 @ 0011a8e6 (size 6) ===== */

void thunk_FUN_00129038(void)

{
  (**(code **)(SysBase + -0xd2))();    /* = SysBase.FreeMem() */
  return;
}



/* ===== thunk_FUN_001280d0 @ 0011a8ec (size 6) ===== */

void thunk_FUN_001280d0(void)

{
  (**(code **)(DOSBase + -0x96))();    /* = DOSBase.LoadSeg() */
  return;
}



/* ===== thunk_FUN_0012801c @ 0011a8f8 (size 6) ===== */

void thunk_FUN_0012801c(void)

{
  (**(code **)(DOSBase + -0x24))();    /* = DOSBase.Close() */
  return;
}



/* ===== thunk_FUN_001291b8 @ 0011a8fe (size 6) ===== */

void thunk_FUN_001291b8(void)

{
  (**(code **)(SysBase + -0x228))();    /* = SysBase.OpenLibrary() */
  return;
}



/* ===== thunk_FUN_00128084 @ 0011a91c (size 6) ===== */

void thunk_FUN_00128084(void)

{
  (**(code **)(DOSBase + -0x5a))();    /* = DOSBase.UnLock() */
  return;
}



/* ===== thunk_FUN_00129000 @ 0011a922 (size 6) ===== */

void thunk_FUN_00129000(void)

{
  (**(code **)(SysBase + -0x84))();    /* = SysBase.Forbid() */
  return;
}



/* ===== thunk_FUN_00129068 @ 0011a934 (size 6) ===== */

void thunk_FUN_00129068(void)

{
  (**(code **)(SysBase + -0xfc))();    /* = SysBase.Remove() */
  return;
}



/* ===== thunk_FUN_00100240 @ 0011a93a (size 6) ===== */

void thunk_FUN_00100240(undefined4 param_1)

{
  undefined **ppuVar1;
  
  for (ppuVar1 = &PTR_PTR_00120050; ppuVar1 != (undefined **)0x0; ppuVar1 = (undefined **)*ppuVar1)
  {
    if (((*(byte *)((int)ppuVar1 + 0x1b) & 4) == 0) && ((*(byte *)((int)ppuVar1 + 0x1b) & 2) != 0))
    {
      if ((int)ppuVar1[1] - (int)ppuVar1[4] != 0) {
        FUN_00100a60(ppuVar1[7],ppuVar1[4],(int)ppuVar1[1] - (int)ppuVar1[4]);
      }
    }
  }
  FUN_0010169c(param_1);
  return;
}



/* ===== thunk_FUN_0012b198 @ 0011a940 (size 6) ===== */

void thunk_FUN_0012b198(void)

{
  (**(code **)(IntuitionBase + -0x108))();    /* = IntuitionBase.SetMenuStrip() */
  return;
}



/* ===== thunk_FUN_00128068 @ 0011a946 (size 6) ===== */

void thunk_FUN_00128068(void)

{
  (**(code **)(DOSBase + -0x54))();    /* = DOSBase.Lock() */
  return;
}



/* ===== thunk_FUN_00129010 @ 0011a94c (size 6) ===== */

void thunk_FUN_00129010(void)

{
  (**(code **)(SysBase + -0x8a))();    /* = SysBase.Permit() */
  return;
}



/* ===== thunk_FUN_00128098 @ 0011a958 (size 6) ===== */

void thunk_FUN_00128098(void)

{
  (**(code **)(DOSBase + -0x66))();    /* = DOSBase.Examine() */
  return;
}



/* ===== thunk_FUN_0012b03c @ 0011a95e (size 6) ===== */

void thunk_FUN_0012b03c(void)

{
  (**(code **)(IntuitionBase + -0x48))();    /* = IntuitionBase.CloseWindow() */
  return;
}



/* ===== thunk_FUN_00129050 @ 0011a964 (size 6) ===== */

void thunk_FUN_00129050(void)

{
  (**(code **)(SysBase + -0xf0))();    /* = SysBase.AddHead() */
  return;
}



/* ===== thunk_FUN_00128030 @ 0011a96a (size 6) ===== */

void thunk_FUN_00128030(void)

{
  (**(code **)(DOSBase + -0x2a))();    /* = DOSBase.Read() */
  return;
}



/* ===== thunk_FUN_0012b0a4 @ 0011a97c (size 6) ===== */

void thunk_FUN_0012b0a4(void)

{
  (**(code **)(IntuitionBase + -0x96))();    /* = IntuitionBase.ModifyIDCMP() */
  return;
}



/* ===== thunk_FUN_00129020 @ 0011a982 (size 6) ===== */

void thunk_FUN_00129020(void)

{
  (**(code **)(SysBase + -0xc6))();    /* = SysBase.AllocMem() */
  return;
}



/* ===== FUN_0011b000 @ 0011b000 (size 1144) ===== */

undefined1 * FUN_0011b000(undefined4 *param_1)

{
  uint uVar1;
  short sVar4;
  undefined4 uVar2;
  int iVar3;
  undefined2 uVar5;
  int **ppiVar6;
  undefined1 *puVar7;
  int *local_50;
  ushort *local_4c;
  ushort *local_48;
  undefined1 *local_44;
  undefined1 *local_40;
  undefined1 *local_3c;
  undefined1 *local_38;
  int *local_34;
  int *local_30;
  int *local_2c;
  int *local_28;
  int *local_24;
  undefined4 local_20;
  uint local_1c;
  int local_18;
  uint local_14;
  int local_10;
  int local_c;
  int local_8;
  
  local_50 = (int *)0x0;
  local_4c = (ushort *)0x0;
  local_8 = *(int *)((int)param_1 + 4);
  if (*(int *)((int)param_1 + 4) == 0) {
    sVar4 = 7;
    ppiVar6 = &local_50;
    puVar7 = &DAT_0011ff2c;
    do {
      *puVar7 = *(undefined1 *)ppiVar6;
      sVar4 = sVar4 + -1;
      ppiVar6 = (int **)((int)ppiVar6 + 1);
      puVar7 = puVar7 + 1;
    } while (sVar4 != -1);
  }
  else {
    param_1 = (undefined4 *)((int)param_1 + 0xe);
    thunk_FUN_0011a000();
    local_4c = (ushort *)thunk_FUN_0011a1ee(0x600,0);
    if (local_4c == (ushort *)0x0) {
      thunk_FUN_0011a0b0();
      sVar4 = 7;
      ppiVar6 = &local_50;
      puVar7 = &DAT_0011ff2c;
      do {
        *puVar7 = *(undefined1 *)ppiVar6;
        sVar4 = sVar4 + -1;
        ppiVar6 = (int **)((int)ppiVar6 + 1);
        puVar7 = puVar7 + 1;
      } while (sVar4 != -1);
    }
    else {
      local_48 = local_4c;
      uVar2 = thunk_FUN_00101604();
      local_50 = (int *)thunk_FUN_0011a1ee(uVar2,0);
      if (local_50 == (int *)0x0) {
        thunk_FUN_0011a0b0();
        sVar4 = 7;
        ppiVar6 = &local_50;
        puVar7 = &DAT_0011ff2c;
        do {
          *puVar7 = *(undefined1 *)ppiVar6;
          sVar4 = sVar4 + -1;
          ppiVar6 = (int **)((int)ppiVar6 + 1);
          puVar7 = puVar7 + 1;
        } while (sVar4 != -1);
      }
      else {
        local_24 = local_50;
        for (local_c = 0; local_c < local_8; local_c = local_c + 1) {
          if (local_8 == local_c + 1) {
            iVar3 = 0;
          }
          else {
            iVar3 = (int)local_24 + 0x1e;
          }
          *local_24 = iVar3;
          sVar4 = thunk_FUN_00101604();
          *(short *)(local_24 + 1) = sVar4 + 10;
          *(undefined2 *)((int)local_24 + 6) = 0;
          *(undefined2 *)(local_24 + 2) = 100;
          *(undefined2 *)((int)local_24 + 10) = 10;
          *(undefined2 *)(local_24 + 3) = 1;
          *(undefined4 *)((int)local_24 + 0xe) = *param_1;
          local_10 = param_1[1];
          uVar2 = thunk_FUN_00101604();
          local_28 = (int *)thunk_FUN_0011a1ee(uVar2,0);
          uVar2 = thunk_FUN_00101604();
          local_38 = (undefined1 *)thunk_FUN_0011a1ee(uVar2,0);
          if ((local_28 == (int *)0x0) || (local_38 == (undefined1 *)0x0)) {
            thunk_FUN_0011a0b0();
            local_50 = (int *)0x0;
            sVar4 = 7;
            ppiVar6 = &local_50;
            puVar7 = &DAT_0011ff2c;
            do {
              *puVar7 = *(undefined1 *)ppiVar6;
              sVar4 = sVar4 + -1;
              ppiVar6 = (int **)((int)ppiVar6 + 1);
              puVar7 = puVar7 + 1;
            } while (sVar4 != -1);
            goto LAB_0011b470;
          }
          *(int **)((int)local_24 + 0x12) = local_28;
          param_1 = (undefined4 *)((int)param_1 + 0xe);
          local_30 = local_28;
          local_40 = local_38;
          for (local_14 = 0; uVar1 = local_14, (int)local_14 < local_10; local_14 = local_14 + 1) {
            if (*(char *)(param_1 + 3) == '\0') {
              local_20 = 0x52;
            }
            else {
              local_20 = 0x56;
            }
            if (local_10 == local_14 + 1) {
              iVar3 = 0;
            }
            else {
              iVar3 = (int)local_30 + 0x22;
            }
            *local_30 = iVar3;
            *(undefined2 *)(local_30 + 1) = 0;
            uVar5 = thunk_FUN_00101604();
            *(undefined2 *)((int)local_30 + 6) = uVar5;
            *(undefined2 *)(local_30 + 2) = 100;
            *(undefined2 *)((int)local_30 + 10) = 10;
            *(short *)(local_30 + 3) = (short)local_20;
            *(undefined4 *)((int)local_30 + 0xe) = 0;
            *(undefined1 **)((int)local_30 + 0x12) = local_40;
            *(undefined4 *)((int)local_30 + 0x16) = 0;
            *(undefined1 *)((int)local_30 + 0x1a) = *(undefined1 *)(param_1 + 3);
            *local_40 = 0;
            local_40[1] = 1;
            local_40[2] = 0;
            *(undefined2 *)(local_40 + 4) = 0;
            *(undefined2 *)(local_40 + 6) = 0;
            *(undefined4 *)(local_40 + 8) = 0;
            *(undefined4 *)(local_40 + 0xc) = *param_1;
            *(undefined4 *)(local_40 + 0x10) = 0;
            if (param_1[2] != 0) {
              *local_48 = (ushort)((uVar1 & 0x3f) << 5) | (ushort)local_c & 0x1f | 0xf800;
              *(undefined4 *)(local_48 + 1) = param_1[2];
              local_48 = local_48 + 3;
            }
            local_18 = param_1[1];
            param_1 = (undefined4 *)((int)param_1 + 0xe);
            if (local_18 == 0) {
              local_30[7] = 0;
            }
            else {
              uVar2 = thunk_FUN_00101604();
              local_2c = (int *)thunk_FUN_0011a1ee(uVar2,0);
              uVar2 = thunk_FUN_00101604();
              local_3c = (undefined1 *)thunk_FUN_0011a1ee(uVar2,0);
              if ((local_2c == (int *)0x0) || (local_3c == (undefined1 *)0x0)) {
                thunk_FUN_0011a0b0();
                local_50 = (int *)0x0;
                sVar4 = 7;
                ppiVar6 = &local_50;
                puVar7 = &DAT_0011ff2c;
                do {
                  *puVar7 = *(undefined1 *)ppiVar6;
                  sVar4 = sVar4 + -1;
                  ppiVar6 = (int **)((int)ppiVar6 + 1);
                  puVar7 = puVar7 + 1;
                } while (sVar4 != -1);
                goto LAB_0011b470;
              }
              local_30[7] = (int)local_2c;
              local_34 = local_2c;
              local_44 = local_3c;
              for (local_1c = 0; uVar1 = local_1c, (int)local_1c < local_18; local_1c = local_1c + 1
                  ) {
                if (*(char *)(param_1 + 3) == '\0') {
                  local_20 = 0x52;
                }
                else {
                  local_20 = 0x56;
                }
                if (local_18 == local_1c + 1) {
                  iVar3 = 0;
                }
                else {
                  iVar3 = (int)local_34 + 0x22;
                }
                *local_34 = iVar3;
                *(undefined2 *)(local_34 + 1) = 0x46;
                sVar4 = thunk_FUN_00101604();
                *(short *)((int)local_34 + 6) = sVar4 + 5;
                *(undefined2 *)(local_34 + 2) = 100;
                *(undefined2 *)((int)local_34 + 10) = 10;
                *(short *)(local_34 + 3) = (short)local_20;
                *(undefined4 *)((int)local_34 + 0xe) = 0;
                *(undefined1 **)((int)local_34 + 0x12) = local_44;
                *(undefined4 *)((int)local_34 + 0x16) = 0;
                *(undefined1 *)((int)local_34 + 0x1a) = *(undefined1 *)(param_1 + 3);
                local_34[7] = 0;
                *local_44 = 0;
                local_44[1] = 1;
                local_44[2] = 0;
                *(undefined2 *)(local_44 + 4) = 0;
                *(undefined2 *)(local_44 + 6) = 0;
                *(undefined4 *)(local_44 + 8) = 0;
                *(undefined4 *)(local_44 + 0xc) = *param_1;
                *(undefined4 *)(local_44 + 0x10) = 0;
                if (param_1[2] != 0) {
                  *local_48 = (ushort)((uVar1 & 0x1f) << 0xb) |
                              (ushort)((local_14 & 0x3f) << 5) | (ushort)local_c & 0x1f;
                  *(undefined4 *)(local_48 + 1) = param_1[2];
                  local_48 = local_48 + 3;
                }
                param_1 = (undefined4 *)((int)param_1 + 0xe);
                local_34 = (int *)((int)local_34 + 0x22);
                local_44 = local_44 + 0x14;
              }
            }
            local_30 = (int *)((int)local_30 + 0x22);
            local_40 = local_40 + 0x14;
          }
          local_24 = (int *)((int)local_24 + 0x1e);
        }
        *local_48 = 0xffff;
        thunk_FUN_0011a00a();
        sVar4 = 7;
        ppiVar6 = &local_50;
        puVar7 = &DAT_0011ff2c;
        do {
          *puVar7 = *(undefined1 *)ppiVar6;
          sVar4 = sVar4 + -1;
          ppiVar6 = (int **)((int)ppiVar6 + 1);
          puVar7 = puVar7 + 1;
        } while (sVar4 != -1);
      }
    }
  }
LAB_0011b470:
  return &DAT_0011ff2c;
}



/* ===== FUN_0011b478 @ 0011b478 (size 52) ===== */

undefined4 FUN_0011b478(int param_1,short param_2)

{
  undefined4 uVar1;
  short *local_8;
  
  local_8 = *(short **)(param_1 + 4);
  while( true ) {
    if (*local_8 == -1) {
      return 0;
    }
    if (*local_8 == param_2) break;
    local_8 = local_8 + 3;
  }
  uVar1 = (**(code **)(local_8 + 1))();
  return uVar1;
}



/* ===== thunk_FUN_00101604 @ 0011b4ac (size 6) ===== */

int thunk_FUN_00101604(void)

{
  uint in_D0;
  uint in_D1;
  
  return (uint)(ushort)((short)(in_D1 >> 0x10) * (short)in_D0 +
                       (short)(in_D0 >> 0x10) * (short)in_D1) * 0x10000 +
         (in_D0 & 0xffff) * (in_D1 & 0xffff);
}



/* ===== thunk_FUN_0011a0b0 @ 0011b4b2 (size 6) ===== */

char thunk_FUN_0011a0b0(void)

{
  int *piVar1;
  undefined4 uStack_8;
  
  uStack_8 = (int *)PTR_DAT_0011ff1c;
  while ((*(char *)((int)uStack_8 + 9) == DAT_0011ff2a &&
         (piVar1 = (int *)*uStack_8, piVar1 != (int *)0x0))) {
    FUN_0011a054(uStack_8);
    uStack_8 = piVar1;
  }
  DAT_0011ff2a = DAT_0011ff2a + -1;
  return DAT_0011ff2a;
}



/* ===== thunk_FUN_0011a00a @ 0011b4b8 (size 6) ===== */

char thunk_FUN_0011a00a(void)

{
  undefined4 uStack_8;
  
  uStack_8 = (int *)PTR_DAT_0011ff1c;
  while ((DAT_0011ff2a == *(char *)((int)uStack_8 + 9) && ((int *)*uStack_8 != (int *)0x0))) {
    *(char *)((int)uStack_8 + 9) = *(char *)((int)uStack_8 + 9) + -1;
    uStack_8 = (int *)*uStack_8;
  }
  DAT_0011ff2a = DAT_0011ff2a + -1;
  return DAT_0011ff2a;
}



/* ===== thunk_FUN_0011a1ee @ 0011b4be (size 6) ===== */

int thunk_FUN_0011a1ee(int param_1,undefined4 param_2)

{
  int iVar1;
  
  iVar1 = thunk_FUN_00129020(param_1 + 0x20,param_2);
  if (iVar1 == 0) {
    iVar1 = 0;
  }
  else {
    FUN_0011a132(iVar1,0,param_1 + 0x20,0);
    iVar1 = iVar1 + 0x20;
  }
  return iVar1;
}



/* ===== thunk_FUN_0011a000 @ 0011b4c4 (size 6) ===== */

char thunk_FUN_0011a000(void)

{
  DAT_0011ff2a = DAT_0011ff2a + '\x01';
  return DAT_0011ff2a;
}



/* ===== FUN_0011c000 @ 0011c000 (size 208) ===== */

void FUN_0011c000(char *param_1)

{
  char cVar1;
  int iVar2;
  
  while (DAT_001230cc < 0x20) {
    for (; ((cVar1 = *param_1, cVar1 == ' ' || (cVar1 == '\t')) || (cVar1 == '\n'));
        param_1 = param_1 + 1) {
    }
    if (*param_1 == '\0') break;
    iVar2 = DAT_001230cc * 4;
    DAT_001230cc = DAT_001230cc + 1;
    if (*param_1 == '\"') {
      param_1 = param_1 + 1;
      *(char **)(&DAT_001230d4 + iVar2) = param_1;
      for (; (*param_1 != '\0' && (*param_1 != '\"')); param_1 = param_1 + 1) {
      }
      if (*param_1 == '\0') {
        thunk_FUN_0010169c(1);
      }
      else {
        *param_1 = '\0';
        param_1 = param_1 + 1;
      }
    }
    else {
      *(char **)(&DAT_001230d4 + iVar2) = param_1;
      for (; ((*param_1 != '\0' && (cVar1 = *param_1, cVar1 != ' ')) &&
             ((cVar1 != '\t' && (cVar1 != '\n')))); param_1 = param_1 + 1) {
      }
      if (*param_1 == '\0') break;
      *param_1 = '\0';
      param_1 = param_1 + 1;
    }
  }
  DAT_001230d0 = DAT_0011d048;
  if (DAT_001230cc != 0) {
    DAT_001230d0 = &DAT_001230d4;
  }
  thunk_FUN_001029e6(DAT_001230cc,DAT_001230d0);
  thunk_FUN_0010169c(0);
  return;
}



/* ===== thunk_FUN_001029e6 @ 0011c0d0 (size 6) ===== */

void thunk_FUN_001029e6(void)

{
  int iVar1;
  
  FUN_001026ae();
  DAT_001201ac = thunk_FUN_0011a000();
  iVar1 = thunk_FUN_00101624(&DAT_00120170);
  if (iVar1 != 0) {
    FUN_00102968();
  }
  FUN_00102814();
  return;
}



/* ===== thunk_FUN_0010169c @ 0011c0d6 (size 6) ===== */

void thunk_FUN_0010169c(undefined4 param_1,undefined4 param_2)

{
  int iVar1;
  int *piVar2;
  
  piVar2 = &DAT_001231a8;
  for (iVar1 = 0; iVar1 < DAT_001200d4; iVar1 = iVar1 + 1) {
    if ((*piVar2 != 0) && ((*piVar2 & 4) == 0)) {
      FUN_0010182c(piVar2[1]);
    }
    piVar2 = piVar2 + 2;
  }
  FUN_0010012e(param_1,param_2);
  return;
}



/* ===== FUN_00124000 @ 00124000 (size 18) ===== */

void FUN_00124000(int *param_1)

{
  *param_1 = (int)param_1;
  *param_1 = *param_1 + 4;
  param_1[1] = 0;
  param_1[2] = (int)param_1;
  return;
}



/* ===== FUN_00125000 @ 00125000 (size 150) ===== */

int FUN_00125000(int param_1,undefined1 param_2)

{
  byte bVar3;
  int iVar1;
  undefined4 uVar2;
  
  bVar3 = FUN_001290a4(0xffffffff);
  if (bVar3 == 0xffffffff) {
    iVar1 = 0;
  }
  else {
    iVar1 = FUN_00129020(0x22,0x10001);
    if (iVar1 == 0) {
      FUN_001290b8((uint)bVar3);
      iVar1 = 0;
    }
    else {
      *(int *)(iVar1 + 10) = param_1;
      *(undefined1 *)(iVar1 + 9) = param_2;
      *(undefined1 *)(iVar1 + 8) = 4;
      *(undefined1 *)(iVar1 + 0xe) = 0;
      *(byte *)(iVar1 + 0xf) = bVar3;
      uVar2 = FUN_0012907c(0);
      *(undefined4 *)(iVar1 + 0x10) = uVar2;
      if (param_1 == 0) {
        FUN_00124000(iVar1 + 0x14);
      }
      else {
        FUN_001290cc(iVar1);
      }
    }
  }
  return iVar1;
}



/* ===== FUN_00125096 @ 00125096 (size 68) ===== */

void FUN_00125096(int param_1)

{
  if (*(int *)(param_1 + 10) != 0) {
    FUN_001290e0(param_1);
  }
  *(undefined1 *)(param_1 + 8) = 0xff;
  *(undefined4 *)(param_1 + 0x14) = 0xffffffff;
  FUN_001290b8(*(undefined1 *)(param_1 + 0xf));
  FUN_00129038(param_1,0x22);
  return;
}



/* ===== FUN_00126000 @ 00126000 (size 20) ===== */

void FUN_00126000(undefined4 param_1)

{
  FUN_00127000(param_1,0x30);
  return;
}



/* ===== FUN_00126014 @ 00126014 (size 16) ===== */

void FUN_00126014(undefined4 param_1)

{
  FUN_00127042(param_1);
  return;
}



/* ===== FUN_00127000 @ 00127000 (size 66) ===== */

int FUN_00127000(int param_1,undefined4 param_2)

{
  int iVar1;
  
  if ((param_1 == 0) || (iVar1 = FUN_00129020(param_2,0x10001), iVar1 == 0)) {
    iVar1 = 0;
  }
  else {
    *(undefined1 *)(iVar1 + 8) = 5;
    *(short *)(iVar1 + 0x12) = (short)param_2;
    *(int *)(iVar1 + 0xe) = param_1;
  }
  return iVar1;
}



/* ===== FUN_00127042 @ 00127042 (size 48) ===== */

undefined4 FUN_00127042(int param_1)

{
  undefined4 uVar1;
  
  if (param_1 == 0) {
    uVar1 = 0;
  }
  else {
    *(undefined1 *)(param_1 + 8) = 0xff;
    *(undefined4 *)(param_1 + 0x14) = 0xffffffff;
    *(undefined4 *)(param_1 + 0x18) = 0xffffffff;
    uVar1 = FUN_00129038(param_1,*(undefined2 *)(param_1 + 0x12));
  }
  return uVar1;
}



/* ===== FUN_00128000 @ 00128000 (size 26) ===== */

void FUN_00128000(void)

{
  (**(code **)(DOSBase + -0x1e))();    /* = DOSBase.Open() */
  return;
}



/* ===== FUN_0012801c @ 0012801c (size 20) ===== */

void FUN_0012801c(void)

{
  (**(code **)(DOSBase + -0x24))();    /* = DOSBase.Close() */
  return;
}



/* ===== FUN_00128030 @ 00128030 (size 26) ===== */

void FUN_00128030(void)

{
  (**(code **)(DOSBase + -0x2a))();    /* = DOSBase.Read() */
  return;
}



/* ===== FUN_0012804c @ 0012804c (size 26) ===== */

void FUN_0012804c(void)

{
  (**(code **)(DOSBase + -0x30))();    /* = DOSBase.Write() */
  return;
}



/* ===== FUN_00128068 @ 00128068 (size 26) ===== */

void FUN_00128068(void)

{
  (**(code **)(DOSBase + -0x54))();    /* = DOSBase.Lock() */
  return;
}



/* ===== FUN_00128084 @ 00128084 (size 20) ===== */

void FUN_00128084(void)

{
  (**(code **)(DOSBase + -0x5a))();    /* = DOSBase.UnLock() */
  return;
}



/* ===== FUN_00128098 @ 00128098 (size 26) ===== */

void FUN_00128098(void)

{
  (**(code **)(DOSBase + -0x66))();    /* = DOSBase.Examine() */
  return;
}



/* ===== FUN_001280b4 @ 001280b4 (size 26) ===== */

void FUN_001280b4(void)

{
  (**(code **)(DOSBase + -0x8a))();    /* = DOSBase.CreateProc() */
  return;
}



/* ===== FUN_001280d0 @ 001280d0 (size 20) ===== */

void FUN_001280d0(void)

{
  (**(code **)(DOSBase + -0x96))();    /* = DOSBase.LoadSeg() */
  return;
}



/* ===== FUN_001280e4 @ 001280e4 (size 20) ===== */

void FUN_001280e4(void)

{
  (**(code **)(DOSBase + -0x9c))();    /* = DOSBase.UnLoadSeg() */
  return;
}



/* ===== FUN_00128120 @ 00128120 (size 26) ===== */

void FUN_00128120(void)

{
  (**(code **)(DOSBase + -0xde))();    /* = DOSBase.Execute() */
  return;
}



/* ===== FUN_00129000 @ 00129000 (size 16) ===== */

void FUN_00129000(void)

{
  (**(code **)(SysBase + -0x84))();    /* = SysBase.Forbid() */
  return;
}



/* ===== FUN_00129010 @ 00129010 (size 16) ===== */

void FUN_00129010(void)

{
  (**(code **)(SysBase + -0x8a))();    /* = SysBase.Permit() */
  return;
}



/* ===== FUN_00129020 @ 00129020 (size 22) ===== */

void FUN_00129020(void)

{
  (**(code **)(SysBase + -0xc6))();    /* = SysBase.AllocMem() */
  return;
}



/* ===== FUN_00129038 @ 00129038 (size 24) ===== */

void FUN_00129038(void)

{
  (**(code **)(SysBase + -0xd2))();    /* = SysBase.FreeMem() */
  return;
}



/* ===== FUN_00129050 @ 00129050 (size 22) ===== */

void FUN_00129050(void)

{
  (**(code **)(SysBase + -0xf0))();    /* = SysBase.AddHead() */
  return;
}



/* ===== FUN_00129068 @ 00129068 (size 20) ===== */

void FUN_00129068(void)

{
  (**(code **)(SysBase + -0xfc))();    /* = SysBase.Remove() */
  return;
}



/* ===== FUN_0012907c @ 0012907c (size 20) ===== */

void FUN_0012907c(void)

{
  (**(code **)(SysBase + -0x126))();    /* = SysBase.FindTask() */
  return;
}



/* ===== FUN_00129090 @ 00129090 (size 20) ===== */

void FUN_00129090(void)

{
  (**(code **)(SysBase + -0x13e))();    /* = SysBase.Wait() */
  return;
}



/* ===== FUN_001290a4 @ 001290a4 (size 20) ===== */

void FUN_001290a4(void)

{
  (**(code **)(SysBase + -0x14a))();    /* = SysBase.AllocSignal() */
  return;
}



/* ===== FUN_001290b8 @ 001290b8 (size 20) ===== */

void FUN_001290b8(void)

{
  (**(code **)(SysBase + -0x150))();    /* = SysBase.FreeSignal() */
  return;
}



/* ===== FUN_001290cc @ 001290cc (size 20) ===== */

void FUN_001290cc(void)

{
  (**(code **)(SysBase + -0x162))();    /* = SysBase.AddPort() */
  return;
}



/* ===== FUN_001290e0 @ 001290e0 (size 20) ===== */

void FUN_001290e0(void)

{
  (**(code **)(SysBase + -0x168))();    /* = SysBase.RemPort() */
  return;
}



/* ===== FUN_001290f4 @ 001290f4 (size 22) ===== */

void FUN_001290f4(void)

{
  (**(code **)(SysBase + -0x16e))();    /* = SysBase.PutMsg() */
  return;
}



/* ===== FUN_0012910c @ 0012910c (size 20) ===== */

void FUN_0012910c(void)

{
  (**(code **)(SysBase + -0x174))();    /* = SysBase.GetMsg() */
  return;
}



/* ===== FUN_00129120 @ 00129120 (size 20) ===== */

void FUN_00129120(void)

{
  (**(code **)(SysBase + -0x17a))();    /* = SysBase.ReplyMsg() */
  return;
}



/* ===== FUN_00129134 @ 00129134 (size 20) ===== */

void FUN_00129134(void)

{
  (**(code **)(SysBase + -0x180))();    /* = SysBase.WaitPort() */
  return;
}



/* ===== FUN_00129148 @ 00129148 (size 20) ===== */

void FUN_00129148(void)

{
  (**(code **)(SysBase + -0x19e))();    /* = SysBase.CloseLibrary() */
  return;
}



/* ===== FUN_00129190 @ 00129190 (size 20) ===== */

void FUN_00129190(void)

{
  (**(code **)(SysBase + -0x1c8))();    /* = SysBase.DoIO() */
  return;
}



/* ===== FUN_001291a4 @ 001291a4 (size 20) ===== */

void FUN_001291a4(void)

{
  (**(code **)(SysBase + -0x1ce))();    /* = SysBase.SendIO() */
  return;
}



/* ===== FUN_001291b8 @ 001291b8 (size 24) ===== */

void FUN_001291b8(void)

{
  (**(code **)(SysBase + -0x228))();    /* = SysBase.OpenLibrary() */
  return;
}



/* ===== FUN_001291d0 @ 001291d0 (size 20) ===== */

void FUN_001291d0(void)

{
  (**(code **)(SysBase + -0x234))();    /* = SysBase.ObtainSemaphore() */
  return;
}



/* ===== FUN_001291e4 @ 001291e4 (size 20) ===== */

void FUN_001291e4(void)

{
  (**(code **)(SysBase + -0x23a))();    /* = SysBase.ReleaseSemaphore() */
  return;
}



/* ===== FUN_0012a000 @ 0012a000 (size 28) ===== */

void FUN_0012a000(void)

{
  (**(code **)(GfxBase + -0x3c))();    /* = GfxBase.Text() */
  return;
}



/* ===== FUN_0012a01c @ 0012a01c (size 26) ===== */

void FUN_0012a01c(void)

{
  (**(code **)(GfxBase + -0xc0))();    /* = GfxBase.LoadRGB4() */
  return;
}



/* ===== FUN_0012a038 @ 0012a038 (size 20) ===== */

void FUN_0012a038(void)

{
  (**(code **)(GfxBase + -0xc6))();    /* = GfxBase.InitRastPort() */
  return;
}



/* ===== FUN_0012a068 @ 0012a068 (size 30) ===== */

void FUN_0012a068(void)

{
  (**(code **)(GfxBase + -0x132))();    /* = GfxBase.RectFill() */
  return;
}



/* ===== FUN_0012a0a0 @ 0012a0a0 (size 24) ===== */

void FUN_0012a0a0(void)

{
  (**(code **)(GfxBase + -0x15c))();    /* = GfxBase.SetBPen() */
  return;
}



/* ===== FUN_0012a0b8 @ 0012a0b8 (size 24) ===== */

void FUN_0012a0b8(void)

{
  (**(code **)(GfxBase + -0x162))();    /* = GfxBase.SetDrMd() */
  return;
}



/* ===== FUN_0012a0d0 @ 0012a0d0 (size 30) ===== */

void FUN_0012a0d0(void)

{
  (**(code **)(GfxBase + -0x186))();    /* = GfxBase.InitBitMap() */
  return;
}



/* ===== FUN_0012a0f0 @ 0012a0f0 (size 30) ===== */

void FUN_0012a0f0(void)

{
  (**(code **)(GfxBase + -0x18c))();    /* = GfxBase.ScrollRaster() */
  return;
}



/* ===== FUN_0012a110 @ 0012a110 (size 40) ===== */

void FUN_0012a110(void)

{
  (**(code **)(GfxBase + -0x25e))();    /* = GfxBase.BltBitMapRastPort() */
  return;
}



/* ===== FUN_0012b000 @ 0012b000 (size 20) ===== */

void FUN_0012b000(void)

{
  (**(code **)(IntuitionBase + -0x36))();    /* = IntuitionBase.ClearMenuStrip() */
  return;
}



/* ===== FUN_0012b014 @ 0012b014 (size 20) ===== */

void FUN_0012b014(void)

{
  (**(code **)(IntuitionBase + -0x3c))();    /* = IntuitionBase.ClearPointer() */
  return;
}



/* ===== FUN_0012b028 @ 0012b028 (size 20) ===== */

void FUN_0012b028(void)

{
  (**(code **)(IntuitionBase + -0x42))();    /* = IntuitionBase.CloseScreen() */
  return;
}



/* ===== FUN_0012b03c @ 0012b03c (size 20) ===== */

void FUN_0012b03c(void)

{
  (**(code **)(IntuitionBase + -0x48))();    /* = IntuitionBase.CloseWindow() */
  return;
}



/* ===== FUN_0012b050 @ 0012b050 (size 26) ===== */

void FUN_0012b050(void)

{
  (**(code **)(IntuitionBase + -0x66))();    /* = IntuitionBase.DoubleClick() */
  return;
}



/* ===== FUN_0012b06c @ 0012b06c (size 28) ===== */

void FUN_0012b06c(void)

{
  (**(code **)(IntuitionBase + -0x6c))();    /* = IntuitionBase.DrawBorder() */
  return;
}



/* ===== FUN_0012b088 @ 0012b088 (size 28) ===== */

void FUN_0012b088(void)

{
  (**(code **)(IntuitionBase + -0x72))();    /* = IntuitionBase.DrawImage() */
  return;
}



/* ===== FUN_0012b0a4 @ 0012b0a4 (size 24) ===== */

void FUN_0012b0a4(void)

{
  (**(code **)(IntuitionBase + -0x96))();    /* = IntuitionBase.ModifyIDCMP() */
  return;
}



/* ===== FUN_0012b0d8 @ 0012b0d8 (size 26) ===== */

void FUN_0012b0d8(void)

{
  (**(code **)(IntuitionBase + -0xae))();    /* = IntuitionBase.OffGadget() */
  return;
}



/* ===== FUN_0012b0f4 @ 0012b0f4 (size 24) ===== */

void FUN_0012b0f4(void)

{
  (**(code **)(IntuitionBase + -0xb4))();    /* = IntuitionBase.OffMenu() */
  return;
}



/* ===== FUN_0012b10c @ 0012b10c (size 26) ===== */

void FUN_0012b10c(void)

{
  (**(code **)(IntuitionBase + -0xba))();    /* = IntuitionBase.OnGadget() */
  return;
}



/* ===== FUN_0012b128 @ 0012b128 (size 24) ===== */

void FUN_0012b128(void)

{
  (**(code **)(IntuitionBase + -0xc0))();    /* = IntuitionBase.OnMenu() */
  return;
}



/* ===== FUN_0012b140 @ 0012b140 (size 20) ===== */

void FUN_0012b140(void)

{
  (**(code **)(IntuitionBase + -0xc6))();    /* = IntuitionBase.OpenScreen() */
  return;
}



/* ===== FUN_0012b154 @ 0012b154 (size 20) ===== */

void FUN_0012b154(void)

{
  (**(code **)(IntuitionBase + -0xcc))();    /* = IntuitionBase.OpenWindow() */
  return;
}



/* ===== FUN_0012b168 @ 0012b168 (size 28) ===== */

void FUN_0012b168(void)

{
  (**(code **)(IntuitionBase + -0xd8))();    /* = IntuitionBase.PrintIText() */
  return;
}



/* ===== FUN_0012b198 @ 0012b198 (size 22) ===== */

void FUN_0012b198(void)

{
  (**(code **)(IntuitionBase + -0x108))();    /* = IntuitionBase.SetMenuStrip() */
  return;
}



/* ===== FUN_0012b1b0 @ 0012b1b0 (size 32) ===== */

void FUN_0012b1b0(void)

{
  (**(code **)(IntuitionBase + -0x10e))();    /* = IntuitionBase.SetPointer() */
  return;
}



/* ===== FUN_0012b1d0 @ 0012b1d0 (size 26) ===== */

void FUN_0012b1d0(void)

{
  (**(code **)(IntuitionBase + -0x114))();    /* = IntuitionBase.SetWindowTitles() */
  return;
}



/* ===== FUN_0012b200 @ 0012b200 (size 20) ===== */

void FUN_0012b200(void)

{
  (**(code **)(IntuitionBase + -0x14a))();    /* = IntuitionBase.IntuiTextLength() */
  return;
}



/* ===== FUN_0012b214 @ 0012b214 (size 30) ===== */

void FUN_0012b214(void)

{
  (**(code **)(IntuitionBase + -0x1b0))();    /* = IntuitionBase.RefreshGList() */
  return;
}



/* ===== FUN_0012b234 @ 0012b234 (size 32) ===== */

void FUN_0012b234(void)

{
  (**(code **)(IntuitionBase + -0x1b6))();    /* = IntuitionBase.AddGList() */
  return;
}



/* ===== FUN_0012b254 @ 0012b254 (size 26) ===== */

void FUN_0012b254(void)

{
  (**(code **)(IntuitionBase + -0x1bc))();    /* = IntuitionBase.RemoveGList() */
  return;
}



/* ===== FUN_0012b270 @ 0012b270 (size 26) ===== */

void FUN_0012b270(void)

{
  (**(code **)(IntuitionBase + -0x1ce))();    /* = IntuitionBase.ActivateGadget() */
  return;
}



