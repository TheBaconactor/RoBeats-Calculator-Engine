-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:10 PM
-- Cached decompilation

local v_u_1 = {
    ["Default"] = 0,
    ["DecalDown"] = 1,
    ["DecalUp"] = 2
}
v_u_1.display_mode_to_name = function(_, p2) --[[ Name: display_mode_to_name ]] --[[ Line: 7 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p2 == v_u_1.Default and "Default (3D)" or (p2 == v_u_1.DecalDown and "2D Mode (Down)" or (p2 == v_u_1.DecalUp and "2D Mode (Up)" or ""));
end;
v_u_1.display_mode_to_preview_assetid = function(_, p3) --[[ Name: display_mode_to_preview_assetid ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p3 == v_u_1.Default and "rbxassetid://8092295436" or (p3 == v_u_1.DecalDown and "rbxassetid://8092295655" or (p3 == v_u_1.DecalUp and "rbxassetid://8092295551" or ""));
end;
return v_u_1;
