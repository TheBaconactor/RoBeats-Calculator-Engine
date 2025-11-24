-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:10 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.Override)
local v_u_2 = require(game.ReplicatedStorage.LobbyDecoration.DecorationClasses.LobbyDecorationBase)
local v_u_3 = require(game.ReplicatedStorage.LobbyDecoration.LobbyDecorationUtil)
local v_u_4 = require(game.ReplicatedStorage.Avatar.SPAvatarUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_9 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v10 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_11 = nil
v10:require_client(function() --[[ Line: 13 ]]
    --[[ Upvalues: (ref 1): v_u_11 ]]
    v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
end)
return {
    ["get_decoration_name"] = function(_) --[[ Name: get_decoration_name ]] --[[ Line: 19 ]]
        return "LobbyTruckGear";
    end,
    ["new"] = function(_, p_u_12) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_6, (copy 6): v_u_7, (ref 7): v_u_11, (copy 8): v_u_8, (copy 9): v_u_9, (copy 10): v_u_4 ]]
        local v13 = v_u_2:new()
        v_u_1:get_base_fn(v13, "on_client_startup")
        v13.on_client_startup = function(_, p14) --[[ Name: on_client_startup ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_12, (ref 3): v_u_5, (ref 4): v_u_6, (ref 5): v_u_7, (ref 6): v_u_11, (ref 7): v_u_8, (ref 8): v_u_9, (ref 9): v_u_4 ]]
            v_u_3:register_webnpc_anchors_on_obj(p14, p_u_12)
            local v_u_15 = v_u_5:new()
            local v16 = p_u_12:FindFirstChild("GearDisplayHumanoids")
            if v16 == nil then
                return v_u_6:warnf("LobbyTruckGear:on_client_startup could not find GearDisplayHumanoids");
            end;
            for _, v17 in pairs(v16:GetChildren()) do
                local v18 = v_u_7:first_child_of_type(v17, "Humanoid")
                if v18 then
                    v_u_15:push_back(v18)
                end;
            end;
            v_u_11:get_gear_shop_available_equipmentids(function(p19) --[[ Line: 39 ]]
                --[[ Upvalues: (copy 1): v_u_15, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_4, (ref 5): v_u_11 ]]
                for _, v20 in v_u_15:key_itr() do
                    local v21 = v_u_8:new()
                    for _, v22 in p19:key_itr() do
                        local v23 = v_u_9:singleton():get_equipment_for_id(v22)
                        if v23 then
                            v21:add(v23:get_avatar_slot(), v22)
                        end;
                    end;
                    local v24 = {}
                    for _, v25 in v21:key_itr() do
                        v24[#v24 + 1] = {
                            ["EquipmentID"] = v25,
                            ["Visible"] = true
                        }
                    end;
                    v_u_4:character_modify_with_equipped_data(v20.Parent, v_u_11:get_default_character_clone(), v24)
                    v_u_11:get_gear_shop_model_humanoids():push_back(v20)
                end;
            end)
        end;
        return v13;
    end
};
