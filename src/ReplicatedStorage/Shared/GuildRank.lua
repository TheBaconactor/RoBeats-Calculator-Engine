-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:09 PM
-- Cached decompilation

local v_u_1 = {
    ["Owner"] = 0,
    ["Admin"] = 1,
    ["Member"] = 2
}
v_u_1.can_invite_members = function(_, p2) --[[ Name: can_invite_members ]] --[[ Line: 7 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p2 == v_u_1.Owner and true or p2 == v_u_1.Admin;
end;
v_u_1.can_set_rank = function(_, p3, _, _) --[[ Name: can_set_rank ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p3 == v_u_1.Owner;
end;
return v_u_1;
