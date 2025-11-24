-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_3 = require(game.ReplicatedStorage.Shared.MatchMode)
return {
    ["new"] = function(_, p4, p_u_5) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3 ]]
        local v6 = {}
        local v_u_7 = v_u_1:new({ p4 })
        local v_u_8 = v_u_1:new()
        v6.add_shine_proto = function(_, p9) --[[ Name: add_shine_proto ]] --[[ Line: 15 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            v_u_7:push_back(p9)
        end;
        local v_u_10 = 1
        local function _() --[[ Name: get_shine_proto ]] --[[ Line: 20 ]]
            --[[ Upvalues: (copy 1): v_u_7, (ref 2): v_u_10 ]]
            local v11 = v_u_7:get(v_u_10)
            v_u_10 = v_u_10 + 1
            if v_u_10 > v_u_7:count() then
                v_u_10 = 1
            end;
            return v11;
        end;
        v6.create_shine_for_slot_at_cframe = function(_, p12, p13, p14) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_7, (ref 3): v_u_10, (copy 4): p_u_5, (copy 5): v_u_8 ]]
            local v15 = v_u_2
            local v16 = v_u_7:get(v_u_10)
            v_u_10 = v_u_10 + 1
            if v_u_10 > v_u_7:count() then
                v_u_10 = 1
            end;
            local v17 = v15:new(v16, p12, p13, p14)
            v17:set_emitter_active(false)
            v17:set_light_active(false)
            v17:set_cframe(p14 + p_u_5)
            v17:add_to_parent(p12._effects:get_effect_root())
            v_u_8:push_back(v17)
            return v17;
        end;
        v6.get_character_shines_list = function(_) --[[ Name: get_character_shines_list ]] --[[ Line: 37 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            return v_u_8;
        end;
        v6.teardown = function(_, p18) --[[ Name: teardown ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            for v19 = 1, v_u_8:count() do
                v_u_8:get(v19):do_remove(p18)
            end;
            v_u_8:clear()
        end;
        v6.update = function(_, p20, p21) --[[ Name: update ]] --[[ Line: 46 ]]
            --[[ Upvalues: (copy 1): v_u_8, (ref 2): v_u_3 ]]
            for _, v22 in v_u_8:key_itr() do
                local v23 = v22:get_game_slot()
                local v24 = false
                local v25
                if p21._players._slots:contains(v23) then
                    v25 = true
                    if v_u_3:get_server_game_instance_player_powerbar_active((p21._players._slots:get(v23))) then
                        v24 = true
                    end;
                else
                    v25 = false
                end;
                v22:set_light_active(v25)
                if p21:show_fullscreen_mobile_ui() then
                    if v23 == p21:get_local_game_slot() then
                        v22:set_emitter_active(v24)
                    else
                        v22:set_emitter_active(false)
                    end;
                else
                    v22:set_emitter_active(v24)
                end;
                v22:update(p20, p21)
            end;
        end;
        return v6;
    end
};
