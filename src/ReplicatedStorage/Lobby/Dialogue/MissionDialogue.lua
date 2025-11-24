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
        ["Starlet"] = "New day, new missions. You know the drill.",
        ["Firsttime"] = true
    },
    {
        ["Starlet"] = "Here\'s what we\'ve got for today."
    }
})
local v_u_10 = v2:new():push_back_table_list({
    {
        ["Starlet"] = "Missing a song? For the easier missions, you can usually find them in the shop."
    },
    {
        ["Starlet"] = "Looking for a hard mode? Try asking around and seeing if anyone else has got it."
    },
    {
        ["Starlet"] = "Need a boost? Try getting some better gear to improve your score."
    },
    {
        ["Starlet"] = "Did you know you can change your keybinds? Go find the \'Helpful Alien\' and set them!"
    }
})
local v_u_11 = v2:new():push_back_table_list({
    {
        ["Starlet"] = "Nice work! Keep it up, and you\'ll go far."
    },
    {
        ["Starlet"] = "Nobody ever said this was gonna be easy, right?"
    },
    {
        ["Starlet"] = "I see that hustle! Keep it up."
    }
})
local v_u_12 = v2:new():push_back_table_list({
    {
        ["Starlet"] = "Rank up! At this rate, you\'ll be a star in no time!"
    }
})
v7.new = function(_, p_u_13, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_12, (copy 6): v_u_11, (copy 7): v_u_1, (copy 8): v_u_9, (ref 9): v_u_8, (copy 10): v_u_10 ]]
    local v17 = {}
    local v_u_18 = nil
    local v_u_19 = nil
    v17.cons = function(p_u_20) --[[ Name: cons ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_5, (copy 3): p_u_16, (ref 4): v_u_3, (copy 5): p_u_15, (ref 6): v_u_19, (copy 7): p_u_14, (copy 8): p_u_13, (ref 9): v_u_4, (ref 10): v_u_6 ]]
        v_u_18 = v_u_5:new("Starlet", p_u_16.StarletDialogue, v_u_3:new(p_u_15, p_u_16.PrimaryPart, p_u_16.StarletDialogue))
        v_u_19 = p_u_14:add_cycle_element(p_u_13, 1, v_u_4:new(v_u_3:new(p_u_14, p_u_16.PrimaryPart, p_u_16.Starlet), p_u_13._spui, function() --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_6, (copy 3): p_u_20 ]]
            p_u_13._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_20:load_from_pressed_dialogues("Starlet")
        end):set_selected_tar_scale(1.05):set_triggered_scale_offset(0.1))
        p_u_20:load_from_startup_dialogues()
    end;
    v17.rankup = function(p21) --[[ Name: rankup ]] --[[ Line: 69 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        p21:load_dialogue(v_u_12:random())
    end;
    v17.item_completed = function(p22) --[[ Name: item_completed ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        p22:load_dialogue(v_u_11:random())
    end;
    v17.load_from_startup_dialogues = function(p23) --[[ Name: load_from_startup_dialogues ]] --[[ Line: 77 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_9, (ref 3): v_u_8 ]]
        local v25 = v_u_1:splist_filter(v_u_9, function(p24) --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            if v_u_8 == false then
                return p24.Firsttime == true;
            else
                return p24.Firsttime ~= true;
            end;
        end)
        v_u_8 = true
        p23:load_dialogue(v25:random())
    end;
    v17.load_from_pressed_dialogues = function(p26, p_u_27) --[[ Name: load_from_pressed_dialogues ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10 ]]
        p26:load_dialogue(v_u_1:splist_filter(v_u_10, function(p28) --[[ Line: 90 ]]
            --[[ Upvalues: (copy 1): p_u_27 ]]
            return p28[p_u_27] ~= nil;
        end):random())
    end;
    v17.load_dialogue = function(_, p29) --[[ Name: load_dialogue ]] --[[ Line: 96 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_18 ]]
        if p29 == nil then
            return;
        else
            local l_Starlet_0 = p29.Starlet
            if l_Starlet_0 == nil then
                v_u_18:finish()
            else
                p_u_13._update_enqueue_fn:enqueue_function(function() --[[ Line: 101 ]]
                    --[[ Upvalues: (ref 1): v_u_18, (copy 2): l_Starlet_0 ]]
                    v_u_18:display_text(l_Starlet_0)
                end, 0)
            end;
        end;
    end;
    local function _(p30) --[[ Name: dialogue_time_finish ]] --[[ Line: 109 ]]
        if p30:is_displayed() and p30:get_time_displayed() > 5 then
            p30:finish()
        end;
    end;
    v17.update = function(_, p31) --[[ Name: update ]] --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18:update(p31)
        local v32 = v_u_18
        if v32:is_displayed() and v32:get_time_displayed() > 5 then
            v32:finish()
        end;
    end;
    v17.layout = function(_) --[[ Name: layout ]] --[[ Line: 121 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18:layout()
    end;
    v17.set_alpha = function(_, p33) --[[ Name: set_alpha ]] --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18:set_alpha(p33)
    end;
    v17:cons()
    return v17;
end;
return v7;
