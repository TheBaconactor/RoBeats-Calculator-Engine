-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:59 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v7 = {}
local v_u_8 = false
local v_u_9 = v2:new():push_back_table_list({
    {
        ["Lisa"] = "Hey there, champ! Think you got what it takes to make it to the top?",
        ["Firsttime"] = true
    },
    {
        ["Lisa"] = "Back to check your rank?\nIt\'s not going up on its own!"
    },
    {
        ["Lisa"] = "To the victor go the spoils.\nI got a feeling that could be you!"
    }
})
local v_u_10 = v2:new():push_back_table_list({
    {
        ["Lisa"] = "Some weirdos just refuse to use any gear at all. Get with the times, I tell em\'!"
    },
    {
        ["Lisa"] = "Wanna improve your rank?\nGet gear and upgrade it!"
    },
    {
        ["Lisa"] = "Gather up some coins and upgrade your gear. That might just give you the extra edge!"
    },
    {
        ["Lisa"] = "The best upgrades require gems.\nYou might get some from competing here!"
    }
})
v7.new = function(_, p_u_11, p_u_12, p_u_13, p_u_14) --[[ Name: new ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_1, (copy 6): v_u_9, (ref 7): v_u_8, (copy 8): v_u_10 ]]
    local v15 = {}
    local v_u_16 = nil
    local v_u_17 = nil
    v15.cons = function(p_u_18) --[[ Name: cons ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_5, (copy 3): p_u_14, (ref 4): v_u_3, (copy 5): p_u_13, (ref 6): v_u_17, (copy 7): p_u_12, (copy 8): p_u_11, (ref 9): v_u_4, (ref 10): v_u_6 ]]
        v_u_16 = v_u_5:new("Lisa", p_u_14.LisaDialogue, v_u_3:new(p_u_13, p_u_14.PrimaryPart, p_u_14.LisaDialogue))
        v_u_17 = p_u_12:add_cycle_element(p_u_11, 1, v_u_4:new(v_u_3:new(p_u_12, p_u_14.PrimaryPart, p_u_14.Lisa), p_u_11._spui, function() --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_6, (copy 3): p_u_18 ]]
            p_u_11._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_18:load_from_pressed_dialogues("Lisa")
        end):set_selected_tar_scale(1.05):set_triggered_scale_offset(0.1))
        p_u_18:load_from_startup_dialogues()
    end;
    v15.load_from_startup_dialogues = function(p19) --[[ Name: load_from_startup_dialogues ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_9, (ref 3): v_u_8 ]]
        local v21 = v_u_1:splist_filter(v_u_9, function(p20) --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            if v_u_8 == false then
                return p20.Firsttime == true;
            else
                return p20.Firsttime ~= true;
            end;
        end)
        v_u_8 = true
        p19:load_dialogue(v21:random())
    end;
    v15.load_from_pressed_dialogues = function(p22, p_u_23) --[[ Name: load_from_pressed_dialogues ]] --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10 ]]
        p22:load_dialogue(v_u_1:splist_filter(v_u_10, function(p24) --[[ Line: 73 ]]
            --[[ Upvalues: (copy 1): p_u_23 ]]
            return p24[p_u_23] ~= nil;
        end):random())
    end;
    v15.load_dialogue = function(_, p25) --[[ Name: load_dialogue ]] --[[ Line: 79 ]]
        --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_16 ]]
        if p25 == nil then
            return;
        else
            local l_Lisa_0 = p25.Lisa
            if l_Lisa_0 == nil then
                v_u_16:finish()
            else
                p_u_11._update_enqueue_fn:enqueue_function(function() --[[ Line: 84 ]]
                    --[[ Upvalues: (ref 1): v_u_16, (copy 2): l_Lisa_0 ]]
                    v_u_16:display_text(l_Lisa_0)
                end, 0)
            end;
        end;
    end;
    local function _(p26) --[[ Name: dialogue_time_finish ]] --[[ Line: 92 ]]
        if p26:is_displayed() and p26:get_time_displayed() > 5 then
            p26:finish()
        end;
    end;
    v15.update = function(_, p27) --[[ Name: update ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        v_u_16:update(p27)
        local v28 = v_u_16
        if v28:is_displayed() and v28:get_time_displayed() > 5 then
            v28:finish()
        end;
    end;
    v15.layout = function(_) --[[ Name: layout ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        v_u_16:layout()
    end;
    v15.set_alpha = function(_, p29) --[[ Name: set_alpha ]] --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        v_u_16:set_alpha(p29)
    end;
    v15:cons()
    return v15;
end;
return v7;
