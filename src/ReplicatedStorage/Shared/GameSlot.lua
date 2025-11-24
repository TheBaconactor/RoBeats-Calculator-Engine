-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:02 PM
-- Cached decompilation

local v_u_1 = {
    ["SLOT_1"] = 1,
    ["SLOT_2"] = 2,
    ["SLOT_3"] = 3,
    ["SLOT_4"] = 4,
    ["SLOT_MIN"] = 1,
    ["SLOT_MAX"] = 4,
    ["_world_center_position"] = Vector3.new()
}
v_u_1.set_world_center_position = function(_, p2) --[[ Name: set_world_center_position ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1._world_center_position = p2
end;
v_u_1.get_world_center_position = function(_) --[[ Name: get_world_center_position ]] --[[ Line: 17 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return v_u_1._world_center_position;
end;
v_u_1.slot_to_world_position = function(_, p3) --[[ Name: slot_to_world_position ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    if p3 == v_u_1.SLOT_1 then
        return Vector3.new(-50, 0, 50) + v_u_1._world_center_position;
    elseif p3 == v_u_1.SLOT_2 then
        return Vector3.new(-50, 0, -50) + v_u_1._world_center_position;
    elseif p3 == v_u_1.SLOT_3 then
        return Vector3.new(50, 0, -50) + v_u_1._world_center_position;
    else
        return Vector3.new(50, 0, 50) + v_u_1._world_center_position;
    end;
end;
v_u_1.slot_to_camera_cframe = function(_, p4, p5, p6, p7) --[[ Name: slot_to_camera_cframe ]] --[[ Line: 39 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v8 = p5 == nil and 36.5 or p5
    local v9 = p6 == nil and 14 or p6
    local v10 = p7 == nil and 17.5 or p7
    if p4 == v_u_1.SLOT_1 then
        return CFrame.new(Vector3.new(-v8, v9, v8) + v_u_1._world_center_position, Vector3.new(-v10, 0, v10) + v_u_1._world_center_position);
    elseif p4 == v_u_1.SLOT_2 then
        return CFrame.new(Vector3.new(-v8, v9, -v8) + v_u_1._world_center_position, Vector3.new(-v10, 0, -v10) + v_u_1._world_center_position);
    elseif p4 == v_u_1.SLOT_3 then
        return CFrame.new(Vector3.new(v8, v9, -v8) + v_u_1._world_center_position, Vector3.new(v10, 0, -v10) + v_u_1._world_center_position);
    else
        return CFrame.new(Vector3.new(v8, v9, v8) + v_u_1._world_center_position, Vector3.new(v10, 0, v10) + v_u_1._world_center_position);
    end;
end;
v_u_1.perp_view_slot = function(_, p11, p12) --[[ Name: perp_view_slot ]] --[[ Line: 71 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    if p11 == v_u_1.SLOT_1 then
        return p12 == v_u_1.SLOT_2 and true or p12 == v_u_1.SLOT_4;
    elseif p11 == v_u_1.SLOT_2 then
        return p12 == v_u_1.SLOT_1 and true or p12 == v_u_1.SLOT_3;
    elseif p11 == v_u_1.SLOT_3 then
        return p12 == v_u_1.SLOT_2 and true or p12 == v_u_1.SLOT_4;
    else
        return p12 == v_u_1.SLOT_1 and true or p12 == v_u_1.SLOT_3;
    end;
end;
v_u_1.slot_to_character_cframe = function(_, p13) --[[ Name: slot_to_character_cframe ]] --[[ Line: 83 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    if p13 == v_u_1.SLOT_1 then
        return CFrame.new(Vector3.new(-15, 3, 31.5) + v_u_1._world_center_position, Vector3.new(-100, 3, 100) + v_u_1._world_center_position);
    elseif p13 == v_u_1.SLOT_2 then
        return CFrame.new(Vector3.new(-31.5, 3, -15) + v_u_1._world_center_position, Vector3.new(-100, 3, -100) + v_u_1._world_center_position);
    elseif p13 == v_u_1.SLOT_3 then
        return CFrame.new(Vector3.new(15, 3, -31.5) + v_u_1._world_center_position, Vector3.new(100, 3, -100) + v_u_1._world_center_position);
    else
        return CFrame.new(Vector3.new(31.5, 3, 15) + v_u_1._world_center_position, Vector3.new(100, 0, 100) + v_u_1._world_center_position);
    end;
end;
return v_u_1;
