-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:26 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.EventString)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v15 = {
            ["_slots"] = v_u_1:new(),
            ["teardown"] = function(p4) --[[ Name: teardown ]] --[[ Line: 19 ]]
                p4._slots:clear()
            end,
            ["contains_player_of_id"] = function(p5, p6) --[[ Name: contains_player_of_id ]] --[[ Line: 24 ]]
                if p5 == nil then
                    return false;
                end;
                for _, v7 in p5._slots:key_itr() do
                    if v7._id == p6 then
                        return true;
                    end;
                end;
                return false;
            end,
            ["get_slot_place"] = function(_, p8, p9) --[[ Name: get_slot_place ]] --[[ Line: 34 ]]
                return p8._ui_manager._place_slots == nil and 0 or p8._ui_manager._place_slots:slot_place(p9);
            end,
            ["update_from_gear_info"] = function(p10, _, p11) --[[ Name: update_from_gear_info ]] --[[ Line: 42 ]]
                if p10 ~= nil then
                    for v12 = 1, 4 do
                        local v13 = p11[v12]
                        local v14 = p10._slots:get(v12)
                        if v13 ~= nil and v14 ~= nil then
                            v14._gear_stats = v13.GearStats
                            v14._equipped = v13.Equipped
                            if v13.DisplayPets ~= nil then
                                v14._display_pet_tab = v13.DisplayPets
                            end;
                        end;
                    end;
                end;
            end
        }
        local v_u_16 = {}
        v15.get_last_player_info_data = function(_) --[[ Name: get_last_player_info_data ]] --[[ Line: 17 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        local v_u_17 = 0
        v15.get_last_updated_time = function(_) --[[ Name: get_last_updated_time ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        v15.update_from_player_info_data = function(p18, p19, p20, p21) --[[ Name: update_from_player_info_data ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_17, (ref 3): v_u_16, (ref 4): v_u_2 ]]
            if p18 ~= nil then
                v_u_3:is_table(p20)
                v_u_17 = tick()
                local v22 = p21 == nil and true or p21
                for v23 = 1, 4 do
                    if p20[v23] ~= nil then
                        local v24 = p20[v23]
                        v_u_3:is_int(v24.Slot)
                        if typeof(v24.Score) ~= "number" then
                            v24.Score = 0
                        end;
                        if typeof(v24.Chain) ~= "number" then
                            v24.Chain = 0
                        end;
                        v_u_3:is_string(v24.Name)
                        v_u_3:is_int(v24.UserId)
                    end;
                end;
                v_u_16 = p20
                for v25, _ in p18._slots:key_itr() do
                    local v26 = false
                    for v27 = 1, 4 do
                        if p20[v27] ~= nil and p20[v27].Slot == v25 then
                            v26 = true
                        end;
                    end;
                    if v26 == false then
                        p18._slots:remove(v25)
                    end;
                end;
                for v28 = 1, 4 do
                    if p20[v28] ~= nil then
                        local v29 = p20[v28]
                        if p18._slots:contains(v29.Slot) == false then
                            p18._slots:add(v29.Slot, v_u_2:new(v29.UserId, v29.Name))
                        end;
                        local v30 = p18._slots:get(v29.Slot)
                        local l__like_count_0 = v30._like_count
                        v30:update_from_player_info(v29)
                        if v29.Slot == p19:get_local_game_slot() and v22 then
                            p19:es_gamelocal_get_scoremanager():update_servergameinstanceplayer_score(v30)
                        end;
                        if v30._like_count < l__like_count_0 then
                            v30._like_count = l__like_count_0
                        end;
                    end;
                end;
            end;
        end;
        return v15;
    end
};
