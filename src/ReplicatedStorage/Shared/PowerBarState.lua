-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:03 PM
-- Cached decompilation

local v_u_1 = {
    ["PowerBar_Charging"] = 0,
    ["PowerBar_Active"] = 1,
    ["ES_FN_TMP1"] = 0,
    ["ES_FN_TMP2"] = 0,
    ["ES_FN_TMP3"] = 0,
    ["ES_FN_TMP4"] = 0
}
v_u_1.active_bool_to_state = function(_, p2) --[[ Name: active_bool_to_state ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    if p2 then
        return v_u_1.PowerBar_Active;
    else
        return v_u_1.PowerBar_Charging;
    end;
end;
return v_u_1;
