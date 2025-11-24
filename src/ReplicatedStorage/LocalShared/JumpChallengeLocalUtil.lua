-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.WebNPCAnchors)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
return {
    ["register_boost_jump_on_collision_obj_list"] = function(_, p5, p_u_6, p7, p_u_8) --[[ Name: register_boost_jump_on_collision_obj_list ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_1 ]]
        local v_u_9 = v_u_4:new()
        local v10 = {}
        for _, v11 in p7:key_itr() do
            v_u_9:push_back((p5._intersect_zone_manager:intersect_zone_from_part(v11)))
        end;
        local v_u_12 = true
        v10.set_enabled = function(_, p13) --[[ Name: set_enabled ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            v_u_12 = p13
        end;
        p5:register_lobby_update_fn(function(p14, p15) --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_1, (copy 3): v_u_9, (copy 4): p_u_6, (copy 5): p_u_8 ]]
            if v_u_12 == true then
                local l_Position_0 = v_u_1:get_localplayer_cframe().Position
                for _, v16 in v_u_9:key_itr() do
                    if v16:contains_point(l_Position_0) then
                        p15._control_script:set_next_jump_as_boosted(true, p_u_6)
                        p15._control_script:force_jump()
                        if p_u_8 then
                            p_u_8(p14, p15)
                        end;
                    end;
                end;
            end;
        end)
        return v10;
    end,
    ["register_name_to_proto_obj_root"] = function(_, p17) --[[ Name: register_name_to_proto_obj_root ]] --[[ Line: 41 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2 ]]
        p17.Parent = nil
        local v18 = v_u_3:new()
        for _, v19 in pairs(p17:GetChildren()) do
            if v19:IsA("Model") and v19.PrimaryPart then
                v18:add(v19.Name, v19)
            else
                v_u_2:warnf("JumpChallengeLocalUtil:register_name_to_proto_obj_root() skipping child(%s) of proto_obj_root(%s)", v19.Name, p17.Name)
            end;
        end;
        return v18;
    end,
    ["spawn_anchor_root_with_name_to_proto_obj"] = function(_, p_u_20, p_u_21) --[[ Name: spawn_anchor_root_with_name_to_proto_obj ]] --[[ Line: 54 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2 ]]
        local v22 = v_u_4:new(p_u_20:GetChildren())
        for _, v23 in v22:key_itr() do
            v23.Parent = nil
        end;
        local v_u_24 = v_u_4:new()
        local function f_handle_anchor_part(p25) --[[ Name: handle_anchor_part ]] --[[ Line: 62 ]]
            --[[ Upvalues: (copy 1): p_u_21, (copy 2): p_u_20, (copy 3): v_u_24 ]]
            local l_Name_0 = p25.Name
            if p25:IsA("BasePart") and p_u_21:contains(l_Name_0) then
                local v26 = p_u_21:get(l_Name_0):Clone()
                v26:SetPrimaryPartCFrame(p25.CFrame)
                v26.Parent = p_u_20
                v_u_24:push_back(v26)
            end;
        end;
        for _, v27 in v22:key_itr() do
            if v27:IsA("Model") then
                for _, v28 in pairs(v27:GetChildren()) do
                    f_handle_anchor_part(v28)
                end;
            elseif v27:IsA("BasePart") or v27:IsA("BasePart") then
                f_handle_anchor_part(v27)
            else
                v_u_2:warnf("LobbyDecorationUtil:spawn_anchor_root_with_name_to_proto_obj() skipping anchor(%s)", v27.Name)
            end;
        end;
        return v_u_24;
    end
};
