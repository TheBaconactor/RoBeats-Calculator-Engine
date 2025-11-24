-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:04 PM
-- Cached decompilation

local v_u_1 = {
    ["MoveToEnvironment"] = "MoveToEnvironment",
    ["MoveToEnvironmentNoPopper"] = "MoveToEnvironmentNoPopper",
    ["DoCollide"] = "DoCollide"
}
v_u_1.apply_group_id = function(_, p2, p_u_3) --[[ Name: apply_group_id ]] --[[ Line: 7 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    for _, v_u_4 in pairs(p2:GetChildren()) do
        local v5 = v_u_4:IsA("BasePart")
        local v6
        if v5 or v_u_4:IsA("Model") then
            v6 = v_u_4:FindFirstChild(v_u_1.DoCollide) ~= nil
        else
            v6 = false
        end;
        if v6 ~= true and v5 then
            pcall(function() --[[ Line: 17 ]]
                --[[ Upvalues: (copy 1): v_u_4, (copy 2): p_u_3 ]]
                v_u_4.CollisionGroupId = p_u_3
            end)
        end;
        if v_u_4:FindFirstChild(v_u_1.MoveToEnvironment) == nil and v_u_4:FindFirstChild(v_u_1.MoveToEnvironmentNoPopper) == nil then
            v_u_1:apply_group_id(v_u_4, p_u_3)
        end;
    end;
end;
v_u_1.new = function(_) --[[ Name: new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7 = {}
    local s_PhysicsService_0 = game:GetService("PhysicsService")
    local function _(p_u_8) --[[ Name: get_or_create_group_name ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): s_PhysicsService_0 ]]
        local v_u_9 = nil
        if pcall(function() --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): s_PhysicsService_0, (copy 3): p_u_8 ]]
            v_u_9 = s_PhysicsService_0:GetCollisionGroupId(p_u_8)
        end) then
            return v_u_9;
        end;
        v_u_9 = s_PhysicsService_0:CreateCollisionGroup(p_u_8)
        return v_u_9;
    end;
    local v_u_10 = nil
    local v_u_11 = "Characters"
    local v_u_12
    if pcall(function() --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): s_PhysicsService_0, (copy 3): v_u_11 ]]
        v_u_10 = s_PhysicsService_0:GetCollisionGroupId(v_u_11)
    end) then
        v_u_12 = v_u_10
    else
        v_u_10 = s_PhysicsService_0:CreateCollisionGroup("Characters")
        v_u_12 = v_u_10
    end;
    s_PhysicsService_0:CollisionGroupSetCollidable("Characters", "Characters", false)
    local v_u_13 = nil
    local v_u_14 = "Transparent"
    local v_u_15
    if pcall(function() --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): s_PhysicsService_0, (copy 3): v_u_14 ]]
        v_u_13 = s_PhysicsService_0:GetCollisionGroupId(v_u_14)
    end) then
        v_u_15 = v_u_13
    else
        v_u_13 = s_PhysicsService_0:CreateCollisionGroup("Transparent")
        v_u_15 = v_u_13
    end;
    s_PhysicsService_0:CollisionGroupSetCollidable("Transparent", "Characters", false)
    s_PhysicsService_0:CollisionGroupSetCollidable("Transparent", "Default", false)
    local function f_add_children_to_group(p16) --[[ Name: add_children_to_group ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): s_PhysicsService_0, (copy 3): f_add_children_to_group ]]
        for _, v17 in pairs(p16:GetChildren()) do
            local v18 = v17:IsA("BasePart")
            local v19
            if v18 or v17:IsA("Model") then
                v19 = v17:FindFirstChild(v_u_1.DoCollide) ~= nil
            else
                v19 = false
            end;
            if v19 ~= true then
                if v18 then
                    s_PhysicsService_0:SetPartCollisionGroup(v17, "Characters")
                else
                    f_add_children_to_group(v17, "Characters")
                end;
            end;
        end;
    end;
    v7.add_to_group = function(_, p20) --[[ Name: add_to_group ]] --[[ Line: 74 ]]
        --[[ Upvalues: (copy 1): f_add_children_to_group ]]
        f_add_children_to_group(p20)
    end;
    v7.get_character_group_id = function(_) --[[ Name: get_character_group_id ]] --[[ Line: 78 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12;
    end;
    v7.get_transparent_group_id = function(_) --[[ Name: get_transparent_group_id ]] --[[ Line: 79 ]]
        --[[ Upvalues: (copy 1): v_u_15 ]]
        return v_u_15;
    end;
    return v7;
end;
return v_u_1;
