-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:16 PM
-- Cached decompilation

local v_u_1 = {
    ["SHIRT"] = 1,
    ["PANTS"] = 2,
    ["HAT"] = 3,
    ["FACE"] = 4,
    ["NECK"] = 5,
    ["BACK"] = 6
}
local v_u_2 = {}
for v3, v4 in pairs(v_u_1) do
    v_u_2[v3] = v4
end;
v_u_1.slot_itr = function(_) --[[ Name: slot_itr ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return pairs(v_u_2);
end;
v_u_1.get_slot_after_value = function(_) --[[ Name: get_slot_after_value ]] --[[ Line: 16 ]]
    return 7;
end;
v_u_1.get_slot_before_value = function(_) --[[ Name: get_slot_before_value ]] --[[ Line: 17 ]]
    return 0;
end;
v_u_1.slot_to_name = function(_, p5) --[[ Name: slot_to_name ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p5 == v_u_1.SHIRT and "Shirt" or (p5 == v_u_1.PANTS and "Pants" or (p5 == v_u_1.HAT and "Hat" or (p5 == v_u_1.FACE and "Face" or (p5 == v_u_1.NECK and "Neck" or "Back"))));
end;
v_u_1.slot_to_attachment_name = function(_, p6) --[[ Name: slot_to_attachment_name ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p6 == v_u_1.HAT and "HatAttachment" or (p6 == v_u_1.FACE and "FaceFrontAttachment" or (p6 == v_u_1.NECK and "NeckAttachment" or (p6 == v_u_1.BACK and "BodyBackAttachment" or nil)));
end;
v_u_1.slot_to_icon = function(_, p7) --[[ Name: slot_to_icon ]] --[[ Line: 49 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p7 == v_u_1.SHIRT and "rbxassetid://1622427378" or (p7 == v_u_1.PANTS and "rbxassetid://1622427379" or (p7 == v_u_1.HAT and "rbxassetid://8699774940" or (p7 == v_u_1.FACE and "rbxassetid://1622425688" or (p7 == v_u_1.NECK and "rbxassetid://1679636251" or "rbxassetid://1622425695"))));
end;
v_u_1.slot_to_icon_outline = function(_, p8) --[[ Name: slot_to_icon_outline ]] --[[ Line: 65 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p8 == v_u_1.SHIRT and "rbxassetid://5870419356" or (p8 == v_u_1.PANTS and "rbxassetid://5870419264" or (p8 == v_u_1.HAT and "rbxassetid://8699775019" or (p8 == v_u_1.FACE and "rbxassetid://5870418979" or (p8 == v_u_1.NECK and "rbxassetid://5870419177" or "rbxassetid://5870418866"))));
end;
v_u_1.Invalid = -1
return v_u_1;
