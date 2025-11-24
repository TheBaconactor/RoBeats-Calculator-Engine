-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:26 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
return {
    ["SFX_HITFXG_DRUM_1"] = "rbxassetid://574838657",
    ["SFX_HITFXG_DRUM_2"] = "rbxassetid://574838433",
    ["SFX_HITFXG_TAMB_1"] = "rbxassetid://864172134",
    ["SFX_HITFXG_TAMB_2"] = "rbxassetid://864172106",
    ["SFX_HITFXG_INDHIHAT_1"] = "rbxassetid://864171976",
    ["SFX_HITFXG_INDHIHAT_2"] = "rbxassetid://864172006",
    ["SFX_HITFXG_INDHIHAT_3"] = "rbxassetid://864172044",
    ["SFX_HITFXG_HIHAT_1"] = "rbxassetid://870818834",
    ["SFX_HITFXG_HIHAT_2"] = "rbxassetid://870818951",
    ["SFX_HITFXG_HIHAT_3"] = "rbxassetid://870819035",
    ["SFX_HITFXG_CLAP_1"] = "rbxassetid://866504380",
    ["SFX_HITFXG_CLAP_2"] = "rbxassetid://866504511",
    ["SFX_HITFXG_JAZZHH_1"] = "rbxassetid://880947857",
    ["SFX_HITFXG_JAZZHH_2"] = "rbxassetid://880947978",
    ["SFX_HITFXG_JAZZHH_3"] = "rbxassetid://880948071",
    ["SFX_DRUM_OKAY"] = "rbxassetid://574838536",
    ["SFX_MISS"] = "rbxassetid://574838230",
    ["SFX_TICK"] = "rbxassetid://574838785",
    ["SFX_COUNTDOWN_READY"] = "rbxassetid://770375074",
    ["SFX_COUNTDOWN_GO"] = "rbxassetid://770373595",
    ["SFX_WOOSH"] = "rbxassetid://770375537",
    ["SFX_ACQUIRE"] = "rbxassetid://770372288",
    ["SFX_BUTTONPRESS"] = "rbxassetid://770372471",
    ["SFX_FANFARE"] = "rbxassetid://770373343",
    ["SFX_MENU_BUY"] = "rbxassetid://770373814",
    ["SFX_MENU_CLOSE"] = "rbxassetid://770373986",
    ["SFX_MENU_OPEN"] = "rbxassetid://770374860",
    ["SFX_MENU_CLOSE_LONG"] = "rbxassetid://770374214",
    ["SFX_MENU_OPEN_LONG"] = "rbxassetid://770374514",
    ["SFX_FAIL"] = "rbxassetid://3554716398",
    ["SFX_CROWD_TEMP"] = "rbxassetid://770373135",
    ["SFX_BOO_1"] = "rbxassetid://786602539",
    ["SFX_ENDCHEER_1"] = "rbxassetid://786602445",
    ["SFX_FEVERCHEER_1"] = "rbxassetid://786602324",
    ["SFX_STARTCHEER_1"] = "rbxassetid://786602174",
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 57 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3, (copy 4): v_u_4 ]]
        local v_u_10 = {
            ["_key_to_pooled_sound"] = v_u_1:new(),
            ["_key_to_active_sound"] = v_u_1:new(),
            ["cons"] = function(_) end,
            ["update"] = function(p5, _) --[[ Name: update ]] --[[ Line: 122 ]]
                for v6, _ in p5._key_to_active_sound:key_itr() do
                    local v7 = p5._key_to_active_sound:list_of(v6)
                    for v8 = v7:count(), 1, -1 do
                        local v9 = v7:get(v8)
                        if v9.Looped == false and v9.Playing == false then
                            p5._key_to_pooled_sound:push_back_to(v6, v9)
                            v7:remove_at(v8)
                        end;
                    end;
                end;
            end
        }
        local l_Folder_0 = Instance.new("Folder", game.Workspace)
        l_Folder_0.Name = v_u_2:gen_name("SFXPooledParent")
        local v_u_11 = v_u_3:new()
        local function f_create_pooled(p12, p13) --[[ Name: create_pooled ]] --[[ Line: 68 ]]
            --[[ Upvalues: (copy 1): v_u_11, (copy 2): l_Folder_0, (copy 3): v_u_10 ]]
            local v14 = p13 == nil and 0.5 or p13
            local v15
            if v_u_11:count() > 0 then
                v15 = v_u_11:pop_back()
            else
                v15 = Instance.new("Sound", l_Folder_0)
            end;
            v15.SoundId = p12
            v15.Playing = false
            v15.Volume = v14
            v_u_10._key_to_pooled_sound:push_back_to(p12, v15)
        end;
        v_u_10.prepool = function(_) --[[ Name: prepool ]] --[[ Line: 89 ]]
            --[[ Upvalues: (copy 1): l_Folder_0, (copy 2): v_u_11 ]]
            for _ = 1, 70 do
                v_u_11:push_back((Instance.new("Sound", l_Folder_0)))
            end;
        end;
        v_u_10.preload = function(_, p16, p17, p18) --[[ Name: preload ]] --[[ Line: 96 ]]
            --[[ Upvalues: (copy 1): f_create_pooled ]]
            for _ = 1, p17 do
                f_create_pooled(p16, p18)
            end;
        end;
        v_u_10.play_sfx = function(p19, p20, p21) --[[ Name: play_sfx ]] --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): f_create_pooled ]]
            if p20 == nil then
                return v_u_4:warnf("SFXManager:play_sfx(nil)");
            end;
            local v22 = p21 == nil and 0.5 or p21
            if p19._key_to_pooled_sound:count_of(p20) == 0 then
                f_create_pooled(p20, v22)
            end;
            local v23 = p19._key_to_pooled_sound:pop_back_from(p20)
            v23.TimePosition = 0
            v23.Looped = false
            v23.Playing = true
            v23.Volume = v22
            p19._key_to_active_sound:push_back_to(p20, v23)
            return v23;
        end;
        v_u_10:cons()
        return v_u_10;
    end
};
